import os
import fitz
import pytest
from PIL import Image, ImageDraw, ImageFont
import io

from app.services.multimodal_service import (
    format_table_as_markdown,
    extract_tables_from_page,
    extract_diagrams_or_figures_from_page,
    extract_scanned_ocr_page,
)
from app.services.pdf_service import extract_pages
from app.services.chunk_service import chunk_pages
from app.services.rag_service import answer_question
from app.services.vector_store import store_embeddings, delete_document
from app.services.embedding_service import generate_embeddings
from app.database.database import SessionLocal
from app.database.models import User, Document


def test_table_markdown_formatter():
    raw_data = [
        ["Model", "Parameters", "Accuracy"],
        ["Llama 3.2", "3B", "92.5%"],
        ["Mistral", "7B", "94.1%"]
    ]
    md = format_table_as_markdown(raw_data)
    assert md is not None
    assert "| Model | Parameters | Accuracy |" in md
    assert "| Llama 3.2 | 3B | 92.5% |" in md
    assert "| Mistral | 7B | 94.1% |" in md


def test_adaptive_scanned_page_extraction(tmp_path):
    """
    Creates a synthetic scanned PDF (rendered image with text, zero machine text)
    and verifies that extract_pages detects the scanned page and extracts OCR text.
    """
    img = Image.new("RGB", (600, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 50), "Confidential Architecture Note: Zero-Trust Security Policy Enabled.", fill=(0, 0, 0))
    draw.text((30, 100), "Server Node Alpha IP: 192.168.10.45", fill=(0, 0, 0))

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    pdf_doc = fitz.open()
    page = pdf_doc.new_page(width=600, height=300)
    page.insert_image(fitz.Rect(0, 0, 600, 300), stream=img_bytes)

    pdf_path = os.path.join(tmp_path, "scanned_doc.pdf")
    pdf_doc.save(pdf_path)
    pdf_doc.close()

    # Run extraction
    pages = extract_pages(pdf_path)
    assert len(pages) == 1
    elements = pages[0]["elements"]
    assert len(elements) >= 1
    
    ocr_element = elements[0]
    assert ocr_element["content_type"] == "ocr"
    assert "Zero-Trust Security Policy" in ocr_element["text"] or "Server Node Alpha" in ocr_element["text"]


def test_multimodal_chunking_and_rag_citation(tmp_path):
    """
    Tests that multimodal chunks (tables, diagrams, text) are chunked with
    proper content_type tags and correctly cited in RAG.
    """
    pages = [
        {
            "page_number": 1,
            "has_images": True,
            "elements": [
                {
                    "content_type": "table",
                    "source_type": "pdf_table",
                    "page_number": 1,
                    "heading": "Database Latency Comparison",
                    "text": "### Database Latency Comparison\n\n| Engine | Read Latency | Write Latency |\n|---|---|---|\n| ChromaDB | 12ms | 25ms |\n| Redis | 2ms | 5ms |"
                },
                {
                    "content_type": "diagram",
                    "source_type": "pdf_visual",
                    "page_number": 1,
                    "heading": "Figure 1: Pipeline Architecture",
                    "text": "### Figure 1: Pipeline Architecture\n**Visual Type**: Diagram\n**Labels & Extracted Components**: Ingestion Worker -> Embedding Engine -> Chroma Vector Store -> CrossEncoder Reranker"
                }
            ]
        }
    ]

    chunks = chunk_pages(pages)
    assert len(chunks) == 2
    types = [c["content_type"] for c in chunks]
    assert "table" in types
    assert "diagram" in types

    # Store in ChromaDB for test user
    user_id = 9999
    doc_id = "test_multimodal_doc_999"
    texts = [c["text"] for c in chunks]
    embeddings = generate_embeddings(texts)

    store_embeddings(
        document_id=doc_id,
        filename="system_architecture.pdf",
        chunks=chunks,
        embeddings=embeddings,
        user_id=user_id
    )

    db = SessionLocal()
    try:
        # Ask question about the table
        res_table = answer_question("What is the read latency of ChromaDB?", user_id, db=db)
        assert "12ms" in res_table["answer"] or "12" in res_table["answer"]
        assert len(res_table["sources"]) > 0
        assert res_table["sources"][0]["content_type"] == "table"

        # Ask question about the diagram
        res_diag = answer_question("What components follow Ingestion Worker in the pipeline architecture?", user_id, db=db)
        assert "Embedding Engine" in res_diag["answer"] or "Chroma" in res_diag["answer"]
        assert len(res_diag["sources"]) > 0
        assert any(s["content_type"] == "diagram" for s in res_diag["sources"])
    finally:
        delete_document(doc_id, user_id)
        db.close()
