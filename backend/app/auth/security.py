import os
import re
from datetime import datetime, timedelta
import bcrypt
from dotenv import load_dotenv
from jose import jwt

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "enterprise-rag-assistant-super-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validates strong password requirements:
    - Minimum 8 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_~`\-+=\[\]\\/]", password):
        return False, "Password must contain at least one special character."
    return True, ""


def hash_password(password: str) -> str:
    # Truncate password to 72 bytes to conform to bcrypt standard
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token