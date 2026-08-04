from fastapi import APIRouter, UploadFile, File, Depends,HTTPException

from app.services.pdf_service import extract_pages
from app.services.chunk_service import chunk_pages
from app.services.embedding_service import generate_embeddings
from app.auth.dependency import get_current_user
from app.database.models import User
from app.core.logging_config import logger

from app.services.vector_store import (
    store_embeddings,
    document_exists
)

from app.services.hash_service import generate_document_id

from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.database.models import Document

import os
import logging

router = APIRouter()

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    # Save uploaded PDF
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Generate unique document id
    document_id = generate_document_id(file_path)

    # Check if already indexed
    if document_exists(document_id):
        return {
            "message": "Document already indexed",
            "document_id": document_id
        }

    # Extract text
    pages = extract_pages(file_path)



    # Chunk text
    chunks = chunk_pages(pages)

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No readable text found in PDF"
        )
    
    texts = [
        chunk["text"]
        for chunk in chunks
    ]
    if not texts:
        raise HTTPException(
            status_code=400,
            detail="PDF contains no extractable text"
        )

    # Generate embeddings
    embeddings = generate_embeddings(texts)

    # Store embeddings in ChromaDB
    store_embeddings(
        document_id=document_id,
        filename=file.filename,
        chunks=chunks,
        embeddings=embeddings,
        user_id=current_user.id

        )

    document = Document(
        document_id=document_id,
        filename=file.filename,
        chunks=len(chunks),
        status="completed",
        user_id=current_user.id
    )


    db.add(document)

    db.commit()

    db.refresh(document)

    logging.info(
    f"Indexed {file.filename} with {len(chunks)} chunks"
)

    return {
        "message": "Document indexed successfully",
        "document_id": document_id,
        "filename": file.filename,
        "chunks_created": len(chunks)
    }