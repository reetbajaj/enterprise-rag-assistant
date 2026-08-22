import os
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.database.models import Document, User
from app.schemas.document import DocumentResponse, DocumentStatsResponse
from app.auth.dependency import get_current_user
from app.services.vector_store import delete_document, count_user_chunks

router = APIRouter()
UPLOAD_DIR = "app/uploads"


@router.get("/documents/stats", response_model=DocumentStatsResponse)
def get_document_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    total = len(docs)
    completed = sum(1 for d in docs if d.status == "completed")
    processing = sum(1 for d in docs if d.status == "processing")
    failed = sum(1 for d in docs if d.status == "failed")
    total_chunks = sum(d.chunks or 0 for d in docs if d.status == "completed")

    return {
        "total_documents": total,
        "completed_documents": completed,
        "processing_documents": processing,
        "failed_documents": failed,
        "total_chunks": total_chunks
    }


@router.get("/documents", response_model=List[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )

    return [
        {
            "document_id": doc.document_id,
            "filename": doc.filename,
            "chunks": doc.chunks or 0,
            "status": doc.status or "uploaded",
            "file_size": doc.file_size or 0,
            "error_message": doc.error_message,
            "uploaded_at": doc.uploaded_at
        }
        for doc in documents
    ]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_single_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = db.query(Document).filter(
        Document.document_id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "chunks": document.chunks or 0,
        "status": document.status or "uploaded",
        "file_size": document.file_size or 0,
        "error_message": document.error_message,
        "uploaded_at": document.uploaded_at
    }


@router.delete("/documents/{document_id}")
def remove_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = db.query(Document).filter(
        Document.document_id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document"
        )

    # 1. Remove vector embeddings from ChromaDB
    try:
        delete_document(document_id, current_user.id)
    except Exception as e:
        logging.warning(f"ChromaDB deletion note for {document_id}: {e}")

    # 2. Remove physical file from disk
    try:
        user_dir = os.path.join(UPLOAD_DIR, f"user_{current_user.id}")
        file_path = os.path.join(user_dir, document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logging.warning(f"Could not remove physical file for {document_id}: {e}")

    # 3. Delete database record
    db.delete(document)
    db.commit()

    return {
        "message": "Document deleted successfully",
        "document_id": document_id
    }