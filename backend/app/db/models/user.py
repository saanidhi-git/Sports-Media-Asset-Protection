from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

if TYPE_CHECKING:
    from .asset import Asset  # noqa: F401

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(String, unique=True, index=True, nullable=False) # e.g., JH-7492
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) # Nullable if only OAuth used
    is_active = Column(Boolean, default=True)
    
    # OAuth Fields
    oauth_provider = Column(String, nullable=True) # google, github, etc.
    oauth_id = Column(String, unique=True, index=True, nullable=True)
    
    # OS Tracking as requested
    operating_system = Column(String, nullable=True) # e.g., win32, linux, darwin
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship: One user can register many assets
    assets = relationship("Asset", back_populates="owner", cascade="all, delete-orphan")
