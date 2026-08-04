from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from typing import List
from app.database.dependency import get_db
from app.database.models import Document
from app.schemas.document import DocumentResponse
from app.schemas.conversations import ConversationResponse

from app.services.vector_store import delete_document


router = APIRouter()


@router.get("/documents", response_model=List[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db)
):

    documents = db.query(
        Document
    ).all()


    return [
        {
            "document_id": doc.document_id,
            "filename": doc.filename,
            "chunks": doc.chunks,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at
        }
        for doc in documents
    ]



@router.delete("/documents/{document_id}")
def remove_document(
    document_id: str,
    db: Session = Depends(get_db)
):

    document = db.query(
        Document
    ).filter(
        Document.document_id == document_id
    ).first()


    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )


    # Delete vectors from ChromaDB
    delete_document(document_id)


    # Delete metadata
    db.delete(document)

    db.commit()


    return {
        "message": "Document deleted successfully",
        "document_id": document_id
    }