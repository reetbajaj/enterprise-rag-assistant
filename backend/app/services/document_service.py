import logging
from app.database.database import SessionLocal
from app.database.models import Document
from app.services.pdf_service import extract_pages
from app.services.chunk_service import chunk_pages
from app.services.embedding_service import generate_embeddings
from app.services.vector_store import store_embeddings


def process_pdf_background(
    document_id: str,
    file_path: str,
    filename: str,
    user_id: int
):
    """
    Background worker that extracts pages, chunks text, computes embeddings,
    indexes into ChromaDB, and updates Document status in SQLite.
    """
    db = SessionLocal()
    try:
        logging.info(f"Starting background processing for doc {document_id} ({filename})")

        # 1. Extract pages (PyMuPDF + EasyOCR fallback)
        pages = extract_pages(file_path)
        if not pages:
            raise ValueError("No extractable pages found in PDF")

        # 2. Chunk pages
        chunks = chunk_pages(pages)
        if not chunks:
            # Check if any page had text
            all_text = "".join(p.get("text", "") for p in pages)
            if not all_text.strip():
                raise ValueError("PDF contains no readable text")
            raise ValueError("Failed to create text chunks from PDF")

        # 3. Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = generate_embeddings(texts)

        # 4. Store in ChromaDB (scoped with user_id)
        store_embeddings(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
            embeddings=embeddings,
            user_id=user_id
        )

        # 5. Update DB record to completed
        doc = db.query(Document).filter(
            Document.document_id == document_id,
            Document.user_id == user_id
        ).first()

        if doc:
            doc.status = "completed"
            doc.chunks = len(chunks)
            doc.error_message = None
            db.commit()
            logging.info(f"Successfully processed {filename}: {len(chunks)} chunks indexed.")

    except Exception as e:
        logging.error(f"Error processing PDF {document_id} ({filename}): {e}", exc_info=True)
        db.rollback()
        try:
            doc = db.query(Document).filter(
                Document.document_id == document_id,
                Document.user_id == user_id
            ).first()
            if doc:
                doc.status = "failed"
                doc.error_message = str(e)
                db.commit()
        except Exception as db_err:
            logging.error(f"Failed to record failure status in DB: {db_err}")
    finally:
        db.close()
