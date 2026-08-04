from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from typing import List

from app.schemas.conversations import ConversationResponse

from app.database.dependency import get_db
from app.database.models import (
    Conversation,
    User
)

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

    conversations = db.query(
        Conversation
    ).filter(
        Conversation.user_id == current_user.id
    ).order_by(
        Conversation.created_at.desc()
    ).all()


    return [
        {
            "question": chat.question,
            "answer": chat.answer,
            "created_at": chat.created_at
        }
        for chat in conversations
    ]