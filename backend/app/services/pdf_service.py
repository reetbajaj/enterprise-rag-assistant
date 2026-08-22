import fitz
import logging
from typing import List, Dict, Any

from app.services.multimodal_service import (
    extract_tables_from_page,
    extract_diagrams_or_figures_from_page,
    extract_scanned_ocr_page,
)


def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Adaptively extracts PDF content page-by-page.
    - Clean text pages: fast PyMuPDF direct text extraction (zero OCR overhead).
    - Scanned/image-only pages: full-page EasyOCR extraction.
    - Tables: structured Markdown table parsing preserving row/col structure.
    - Diagrams/Figures: high-res visual OCR parsing of architecture diagrams, charts, and workflow labels.
    """
    pages = []
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logging.error(f"Failed to open PDF at {pdf_path}: {e}")
        raise ValueError(f"Could not open PDF file: {str(e)}")

    try:
        inherited_table_headers = None

        for page_num, page in enumerate(doc):
            page_idx = page_num + 1
            direct_text = page.get_text("text").strip()
            num_images = len(page.get_images())
            num_drawings = len(page.get_drawings())
            has_visuals = num_images > 0 or num_drawings > 5

            page_elements = []

            # Structured tables are extracted first. Their schema can be carried
            # across continuation pages without knowing anything about the document.
            tables = extract_tables_from_page(
                page,
                page_idx,
                inherited_headers=inherited_table_headers,
            )
            table_bboxes = [t.get("bbox") for t in tables if t.get("bbox") is not None]
            for t in tables:
                if t.get("table_headers") and t.get("chunk_type") == "table":
                    inherited_table_headers = list(t["table_headers"])
                page_elements.append(t)

            # Preserve only non-table page text when structured tables were found.
            # This prevents a giant flattened copy of the table from competing with
            # the structured table/row evidence during retrieval.
            if table_bboxes:
                non_table_parts = []
                try:
                    for block in page.get_text("blocks"):
                        if len(block) < 5:
                            continue
                        bx0, by0, bx1, by1, block_text = block[:5]
                        block_rect = fitz.Rect(bx0, by0, bx1, by1)
                        overlaps_table = any(
                            block_rect.intersects(fitz.Rect(*bbox))
                            for bbox in table_bboxes
                            if bbox and len(bbox) == 4
                        )
                        if not overlaps_table and str(block_text).strip():
                            non_table_parts.append(str(block_text).strip())
                except Exception:
                    non_table_parts = []

                clean_non_table = "\n".join(non_table_parts).strip()
                if clean_non_table:
                    page_elements.append({
                        "content_type": "text",
                        "source_type": "pdf_text",
                        "page_number": page_idx,
                        "heading": "",
                        "text": clean_non_table,
                    })

            # Scanned/image-only pages: OCR only when direct text is insufficient.
            if len(direct_text) < 50 and has_visuals and not table_bboxes:
                ocr_elem = extract_scanned_ocr_page(page, page_idx)
                if ocr_elem:
                    page_elements.append(ocr_elem)
            elif len(direct_text) >= 50 and not table_bboxes:
                page_elements.append({
                    "content_type": "text",
                    "source_type": "pdf_text",
                    "page_number": page_idx,
                    "heading": "",
                    "text": direct_text
                })

                if has_visuals:
                    visual_elements = extract_diagrams_or_figures_from_page(
                        page, page_idx, table_bboxes=table_bboxes
                    )
                    page_elements.extend(visual_elements)
            elif has_visuals:
                # A page can contain both structured tables and a separate diagram.
                visual_elements = extract_diagrams_or_figures_from_page(
                    page, page_idx, table_bboxes=table_bboxes
                )
                page_elements.extend(visual_elements)

            pages.append({
                "page_number": page_idx,
                "text": direct_text,
                "has_images": has_visuals,
                "elements": page_elements
            })

    finally:
        doc.close()

    return pages