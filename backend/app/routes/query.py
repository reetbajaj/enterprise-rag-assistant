from fastapi import APIRouter,Depends
from pydantic import BaseModel

from app.services.rag_service import answer_question
from app.auth.dependency import get_current_user
from app.database.models import User, Conversation
from app.database.dependency import get_db
from app.core.logging_config import logger
from sqlalchemy.orm import Session

router = APIRouter()


class QueryRequest(BaseModel):
    question: str



@router.post("/query")
async def query_document(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    result = answer_question(
        request.question,
        current_user.id
    )
    logger.info(
        f"Query executed by user={current_user.id}: {request.question}"
    )
    conversation = Conversation(
        user_id=current_user.id,
        question=request.question,
        answer=result["answer"]
    )


    db.add(conversation)

    db.commit()

    return result