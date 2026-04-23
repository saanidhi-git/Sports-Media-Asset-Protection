from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

if TYPE_CHECKING:
    from .scan_job import ScanJob  # noqa: F401
    from .detection_result import DetectionResult  # noqa: F401

class ScrapedVideo(Base):
    __tablename__ = "scraped_videos"

    id = Column(Integer, primary_key=True, index=True)
    scan_job_id = Column(Integer, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    
    platform = Column(String, index=True, nullable=False) # youtube, reddit, instagram
    platform_video_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    local_folder_path = Column(String, nullable=True)
    frame_paths = Column(JSON, default=[])
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scan_job = relationship("ScanJob", back_populates="scraped_videos")
    frames = relationship("ScrapedFrame", back_populates="scraped_video", cascade="all, delete-orphan")
    detection_results = relationship("DetectionResult", back_populates="scraped_video", cascade="all, delete-orphan")
