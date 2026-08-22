from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from typing import Optional
from sqlalchemy.orm import Session

from app.database.dependency import get_db
from app.database.models import User
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    validate_password_strength
)
from app.auth.dependency import get_current_user


router = APIRouter(
    prefix="/auth"
)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str



@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    clean_email = request.email.strip().lower()
    if "@" not in clean_email or len(clean_email) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required"
        )

    # Validate strong password
    is_valid, err_msg = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )

    existing_user = db.query(User).filter(
        User.email == clean_email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists with this email"
        )

    user = User(
        email=clean_email,
        hashed_password=hash_password(request.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({
        "user_id": user.id,
        "email": user.email
    })

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "email": user.email,
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/login")
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    email = None
    password = None

    # Handle Content-Type: JSON vs Form Data
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
    else:
        try:
            form = await request.form()
            email = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            pass

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    clean_email = email.strip().lower()
    user = db.query(User).filter(
        User.email == clean_email
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({
        "user_id": user.id,
        "email": user.email
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email
        }
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email
    }