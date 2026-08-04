from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.database.database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey
)

from datetime import datetime



class Document(Base):

    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    document_id = Column(
        String,
        unique=True,
        index=True
    )


    filename = Column(
        String
    )


    chunks = Column(
        Integer
    )

    status = Column(
        String,
        default="uploaded"
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )
    
class Conversation(Base):

    __tablename__ = "conversations"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )


    question = Column(
        String
    )


    answer = Column(
        String
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

class User(Base):

    __tablename__ = "users"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    email = Column(
        String,
        unique=True,
        index=True
    )


    hashed_password = Column(
        String
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )