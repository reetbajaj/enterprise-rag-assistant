import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.dependency import get_db
from app.database.models import Conversation, Message, User
from app.auth.dependency import get_current_user
from app.schemas.conversations import (
    ConversationSummaryResponse,
    ConversationDetailResponse,
    ConversationCreateRequest,
    ConversationUpdateRequest,
    MessageResponse
)

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"]
)


@router.get("", response_model=List[ConversationSummaryResponse])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all conversations for the authenticated user."""
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
        .all()
    )

    result = []
    for conv in convs:
        # Get message count and last message preview
        msgs = conv.messages
        msg_count = len(msgs)
        last_preview = msgs[-1].content[:60] + ("..." if len(msgs[-1].content) > 60 else "") if msgs else None

        result.append({
            "id": conv.id,
            "title": conv.title,
            "user_id": conv.user_id,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at or conv.created_at,
            "message_count": msg_count,
            "last_message_preview": last_preview
        })

    return result


@router.post("", response_model=ConversationSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    request: ConversationCreateRequest = ConversationCreateRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation."""
    title = (request.title or "New Conversation").strip()
    if not title:
        title = "New Conversation"

    conv = Conversation(
        title=title,
        user_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    return {
        "id": conv.id,
        "title": conv.title,
        "user_id": conv.user_id,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "message_count": 0,
        "last_message_preview": None
    }


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details and all messages of a specific conversation."""
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    formatted_messages = []
    for msg in conv.messages:
        sources_parsed = []
        if msg.sources_json:
            try:
                sources_parsed = json.loads(msg.sources_json)
            except Exception:
                sources_parsed = []

        formatted_messages.append({
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "role": msg.role,
            "content": msg.content,
            "sources": sources_parsed,
            "latency_seconds": msg.latency_seconds,
            "created_at": msg.created_at
        })

    return {
        "id": conv.id,
        "title": conv.title,
        "user_id": conv.user_id,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at or conv.created_at,
        "messages": formatted_messages
    }


@router.patch("/{conversation_id}", response_model=ConversationSummaryResponse)
def rename_conversation(
    conversation_id: int,
    request: ConversationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rename an existing conversation."""
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    new_title = request.title.strip()
    if not new_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation title cannot be empty"
        )

    conv.title = new_title
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conv)

    msg_count = len(conv.messages)
    last_preview = conv.messages[-1].content[:60] + ("..." if len(conv.messages[-1].content) > 60 else "") if conv.messages else None

    return {
        "id": conv.id,
        "title": conv.title,
        "user_id": conv.user_id,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "message_count": msg_count,
        "last_message_preview": last_preview
    }


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a single conversation and all its messages."""
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    db.delete(conv)
    db.commit()

    return {
        "message": f"Conversation '{conv.title}' deleted successfully",
        "conversation_id": conversation_id
    }


@router.delete("")
def clear_all_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all conversations and messages for the current user."""
    convs = db.query(Conversation).filter(Conversation.user_id == current_user.id).all()
    count = len(convs)
    for conv in convs:
        db.delete(conv)
    db.commit()

    return {
        "message": "All conversations cleared successfully",
        "deleted_count": count
    }
