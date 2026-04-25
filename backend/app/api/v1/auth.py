"""Auth routes: login + user registration/profile."""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core import security
from app.core.config import settings
from app.db.models.user import User
from app.schemas.token import Token
from app.schemas.user import User as UserSchema, UserCreate

router = APIRouter(tags=["Auth"])


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """OAuth2 token login."""
    # Try to find user by email or operator_id
    user = db.query(User).filter(
        or_(
            User.email == form_data.username.lower(),
            User.operator_id == form_data.username
        )
    ).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(user.id, expires_delta=expires),
        "token_type":   "bearer",
    }


@router.post("/users/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """Create a new user account."""
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    if db.query(User).filter(User.operator_id == user_in.operator_id).first():
        raise HTTPException(status_code=400, detail="Operator ID already taken.")

    user = User(
        email=user_in.email.lower(),
        hashed_password=security.get_password_hash(user_in.password),
        operator_id=user_in.operator_id,
        operating_system=user_in.operating_system,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/me", response_model=UserSchema)
def read_user_me(current_user: User = Depends(get_current_user)) -> Any:
    """Get the currently authenticated user."""
    return current_user
