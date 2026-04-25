from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

if TYPE_CHECKING:
    from .scraped_video import ScrapedVideo  # noqa: F401
    from .asset import Asset  # noqa: F401
    from .judge_review import JudgeReview  # noqa: F401

class DetectionResult(Base):
    __tablename__ = "detection_results"

    id = Column(Integer, primary_key=True, index=True)
    scraped_video_id = Column(Integer, ForeignKey("scraped_videos.id", ondelete="CASCADE"), nullable=False)
    matched_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    
    phash_score = Column(Float, nullable=False, default=0.0)
    pdq_score = Column(Float, nullable=False, default=0.0)
    audio_score = Column(Float, nullable=False, default=0.0)
    metadata_score = Column(Float, nullable=False, default=0.0)
    final_score = Column(Float, nullable=False, default=0.0)
    
    verdict = Column(String, nullable=False, index=True) # FLAG, REVIEW, DROP
    
    ai_decision = Column(String, nullable=True)
    ai_reason = Column(Text, nullable=True)
    
    dispatch_status = Column(String, nullable=False, default="PENDING") # PENDING, DISPATCHED
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scraped_video = relationship("ScrapedVideo", back_populates="detection_results")
    matched_asset = relationship("Asset")
    judge_review = relationship("JudgeReview", back_populates="detection_result", uselist=False, cascade="all, delete-orphan")
