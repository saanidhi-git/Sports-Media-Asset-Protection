from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.db.base import User
from app.schemas.user import UserCreate, User as UserSchema

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserSchema)
async def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.post("/register", response_model=UserSchema)
async def register_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate
) -> Any:
    """
    Create new user.
    """
    print(f"Registering user: {user_in.email}")
    try:
        user = db.query(User).filter(User.email == user_in.email).first()
        if user:
            print("Email already exists")
            raise HTTPException(
                status_code=400,
                detail="A user with this email already exists.",
            )
        
        user = db.query(User).filter(User.operator_id == user_in.operator_id).first()
        if user:
            print("Operator ID already exists")
            raise HTTPException(
                status_code=400,
                detail="A user with this operator ID already exists.",
            )

        db_obj = User(
            email=user_in.email,
            hashed_password=security.get_password_hash(user_in.password),
            operator_id=user_in.operator_id,
            operating_system=user_in.operating_system,
            is_active=True,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        print(f"User created successfully: {db_obj.id}")
        return db_obj
    except HTTPException:
        # Re-raise HTTP exceptions (like email already exists)
        raise
    except Exception as e:
        print(f"Database error during registration: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"System error: {str(e)}"
        )
