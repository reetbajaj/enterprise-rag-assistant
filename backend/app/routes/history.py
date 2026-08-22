from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas.conversations import ConversationResponse
from app.database.dependency import get_db
from app.database.models import Conversation, Message, User
from app.auth.dependency import get_current_user

router = APIRouter()


@router.get(
    "/history",
    response_model=List[ConversationResponse]
)
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Backward-compatible flat history of user questions and assistant answers."""
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.asc())
        .all()
    )

    result = []
    for conv in convs:
        msgs = conv.messages
        # Pair user messages and assistant messages
        i = 0
        while i < len(msgs):
            if msgs[i].role == "user":
                q_text = msgs[i].content
                a_text = ""
                if i + 1 < len(msgs) and msgs[i + 1].role == "assistant":
                    a_text = msgs[i + 1].content
                    i += 1
                result.append({
                    "id": msgs[i].id,
                    "question": q_text,
                    "answer": a_text,
                    "created_at": msgs[i].created_at
                })
            i += 1

    return result


@router.delete("/history")
def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Backward-compatible clear all history endpoint."""
    convs = db.query(Conversation).filter(Conversation.user_id == current_user.id).all()
    deleted_count = len(convs)
    for conv in convs:
        db.delete(conv)
    db.commit()

    return {
        "message": "Chat history cleared successfully",
        "deleted_count": deleted_count
    }