from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    operator_id: Optional[str] = None
    operating_system: Optional[str] = None

# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str
    operator_id: str

# Properties to return via API
class User(UserBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
