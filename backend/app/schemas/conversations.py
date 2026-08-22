import json
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional, Any


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: str
    content: str
    sources: Optional[List[Any]] = None
    latency_seconds: Optional[float] = None
    created_at: datetime


class ConversationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message_preview: Optional[str] = None


class ConversationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    user_id: int
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = "New Conversation"


class ConversationUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


# Backward compatibility
class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: Optional[str] = None
    answer: Optional[str] = None
    created_at: Optional[datetime] = None