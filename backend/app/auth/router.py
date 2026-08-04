from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.database.models import User
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token
)


router = APIRouter(
    prefix="/auth"
)



@router.post("/register")
def register(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):

    existing_user = db.query(
        User
    ).filter(
        User.email == email
    ).first()


    if existing_user:

        return {
            "message":"User already exists"
        }


    user = User(
        email=email,
        hashed_password=hash_password(password)
    )


    db.add(user)

    db.commit()

    db.refresh(user)


    return {
        "message":"User created successfully",
        "user_id":user.id
    }

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = db.query(
        User
    ).filter(
        User.email == form_data.username
    ).first()


    if not user:
        return {
            "error": "Invalid credentials"
        }


    if not verify_password(
        form_data.password,
        user.hashed_password
    ):
        return {
            "error": "Invalid credentials"
        }


    token = create_access_token(
        {
            "user_id": user.id,
            "email": user.email
        }
    )


    return {
        "access_token": token,
        "token_type": "bearer"
    }