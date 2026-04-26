from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

if TYPE_CHECKING:
    from .user import User  # noqa: F401

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_name = Column(String, index=True, nullable=False)
    owner_company = Column(String, index=True, nullable=False)
    match_description = Column(Text, nullable=True)
    
    # File Paths
    media_file_path = Column(String, nullable=False)
    scoreboard_file_path = Column(String, nullable=True)
    
    # Scraping Preferences
    scrap_youtube = Column(Boolean, default=False)
    scrap_reddit = Column(Boolean, default=False)
    scrap_instagram = Column(Boolean, default=False)
    
    # Extraction settings
    total_frames = Column(Integer, default=0)
    audio_fp = Column(Text, nullable=True) # Audio fingerprint (using Text for longer length)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    
    # Relationship
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner = relationship("User", back_populates="assets")
    frames = relationship("AssetFrame", back_populates="asset", cascade="all, delete-orphan")
    detection_results = relationship("DetectionResult", back_populates="matched_asset", cascade="all, delete-orphan")
