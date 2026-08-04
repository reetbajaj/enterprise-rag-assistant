from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):

    document_id: str
    filename: str
    chunks: int
    status: str
    uploaded_at: datetime


    class Config:
        from_attributes = True