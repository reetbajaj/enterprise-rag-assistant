from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    filename: str
    chunks: Optional[int] = 0
    status: str
    file_size: Optional[int] = 0
    error_message: Optional[str] = None
    uploaded_at: datetime


class DocumentStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_documents: int
    completed_documents: int
    processing_documents: int
    failed_documents: int
    total_chunks: int