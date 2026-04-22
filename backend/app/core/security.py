from datetime import datetime, timedelta, timezone
from typing import Any, Union
import logging
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Fix for passlib compatibility with bcrypt 4.0+
# (prevents the 'bcrypt' has no attribute '__about__' error)
import bcrypt
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("About", (object,), {"__version__": "4.0.0"})

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Bcrypt has a maximum limit of 72 bytes. 
    # Truncate manually to avoid the "password cannot be longer than 72 bytes" error.
    return pwd_context.verify(plain_password[:72], hashed_password)

def get_password_hash(password: str) -> str:
    # Bcrypt has a maximum limit of 72 bytes.
    return pwd_context.hash(password[:72])
