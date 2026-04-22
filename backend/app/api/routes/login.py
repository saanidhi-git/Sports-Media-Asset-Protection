from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.base import User
from app.schemas.token import Token

router = APIRouter(tags=["Login"])

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    print(f"Login attempt for: {form_data.username}")
    
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        print(f"User not found: {form_data.username}")
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    if not security.verify_password(form_data.password, user.hashed_password):
        print(f"Invalid password for: {form_data.username}")
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    if not user.is_active:
        print(f"Inactive user: {form_data.username}")
        raise HTTPException(status_code=400, detail="Inactive user")
    
    print(f"Login successful for: {form_data.username}")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/login/oauth/{provider}")
async def login_oauth(
    provider: str,
    db: Session = Depends(deps.get_db),
    # This would receive the code/token from the OAuth provider (Google/Github)
) -> Any:
    """
    Skeleton for OAuth login. You can conclude OAuth flow here.
    Supports flexible login: either traditional JWT or OAuth.
    """
    # 1. Verify provider token
    # 2. Check if user with oauth_id exists
    # 3. If not, check if user with email exists and link them
    # 4. Or create a new user
    # 5. Return access_token
    return {"message": f"OAuth login for {provider} not yet implemented"}
