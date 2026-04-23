from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

if TYPE_CHECKING:
    from .user import User  # noqa: F401
    from .scraped_video import ScrapedVideo  # noqa: F401

class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    search_query = Column(String, nullable=False)
    platforms = Column(JSON, nullable=False) # e.g., ["youtube", "reddit"]
    
    status = Column(String, default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="scan_jobs")
    scraped_videos = relationship("ScrapedVideo", back_populates="scan_job", cascade="all, delete-orphan")
