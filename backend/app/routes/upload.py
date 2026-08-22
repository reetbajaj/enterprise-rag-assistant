import os
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.auth.dependency import get_current_user
from app.database.dependency import get_db
from app.database.models import User, Document
from app.services.hash_service import generate_document_id
from app.services.document_service import process_pdf_background

router = APIRouter()

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validate file extension
    raw_filename = file.filename or "document.pdf"
    if not raw_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF (.pdf) files are supported"
        )

    # 2. Sanitize filename against directory traversal
    safe_filename = os.path.basename(raw_filename).replace("..", "").strip()
    if not safe_filename:
        safe_filename = "uploaded_document.pdf"

    # 3. Create user-specific upload directory
    user_dir = os.path.join(UPLOAD_DIR, f"user_{current_user.id}")
    os.makedirs(user_dir, exist_ok=True)

    # 4. Read file content and check size
    content = await file.read()
    file_size = len(content)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)"
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed limit (50MB)"
        )

    file_path = os.path.join(user_dir, safe_filename)
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # 5. Generate unique user-scoped document ID
    document_id = generate_document_id(file_path, user_id=current_user.id)

    # 6. Create initial database record with status="processing"
    doc_record = Document(
        document_id=document_id,
        filename=safe_filename,
        file_size=file_size,
        chunks=0,
        status="processing",
        user_id=current_user.id
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    # 7. Queue background processing task
    background_tasks.add_task(
        process_pdf_background,
        document_id=document_id,
        file_path=file_path,
        filename=safe_filename,
        user_id=current_user.id
    )

    logging.info(f"Queued background processing for {safe_filename} (id={document_id}) for user {current_user.id}")

    return {
        "message": "File uploaded successfully. Processing started in background.",
        "document_id": document_id,
        "filename": safe_filename,
        "file_size": file_size,
        "status": "processing"
    }