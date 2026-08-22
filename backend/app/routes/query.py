import json
import time
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.rag_service import answer_question
from app.auth.dependency import get_current_user
from app.database.models import User, Conversation, Message
from app.database.dependency import get_db
from app.core.logging_config import logger

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[int] = None


@router.post("/query")
async def query_document(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    clean_question = request.question.strip()
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )

    # 1. Resolve or create Conversation
    conversation = None
    if request.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id
            )
            .first()
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        # Create a new conversation with auto-generated title
        auto_title = clean_question[:40] + ("..." if len(clean_question) > 40 else "")
        conversation = Conversation(
            title=auto_title,
            user_id=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # If conversation has default title, update with question
    if conversation.title in ["New Conversation", "New Chat"]:
        conversation.title = clean_question[:40] + ("..." if len(clean_question) > 40 else "")

    # 2. Execute RAG pipeline
    start_time = time.time()
    try:
        result = answer_question(
            clean_question,
            current_user.id,
            db=db
        )
    except Exception as e:
        logger.error(f"Error executing RAG query for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while answering your question: {str(e)}"
        )

    elapsed_time = round(time.time() - start_time, 2)
    logger.info(
        f"Query executed by user={current_user.id} in {elapsed_time}s: '{clean_question[:50]}'"
    )

    # 3. Persist Messages to Conversation in SQLite
    user_msg_id = None
    assistant_msg_id = None
    try:
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=clean_question,
            created_at=datetime.utcnow()
        )
        db.add(user_msg)

        sources_serialized = json.dumps(result.get("sources", []))
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
            sources_json=sources_serialized,
            latency_seconds=elapsed_time,
            created_at=datetime.utcnow()
        )
        db.add(assistant_msg)

        conversation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user_msg)
        db.refresh(assistant_msg)

        user_msg_id = user_msg.id
        assistant_msg_id = assistant_msg.id
    except Exception as db_err:
        logger.warning(f"Failed to record message in DB: {db_err}")

    result["latency_seconds"] = elapsed_time
    result["conversation_id"] = conversation.id
    result["message_id"] = assistant_msg_id

    return result