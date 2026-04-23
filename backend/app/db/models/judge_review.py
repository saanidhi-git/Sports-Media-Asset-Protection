from typing import TYPE_CHECKING
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

if TYPE_CHECKING:
    from .detection_result import DetectionResult  # noqa: F401
    from .user import User  # noqa: F401

class JudgeReview(Base):
    __tablename__ = "judge_reviews"

    id = Column(Integer, primary_key=True, index=True)
    detection_result_id = Column(Integer, ForeignKey("detection_results.id", ondelete="CASCADE"), nullable=False, unique=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    decision = Column(String, nullable=False, index=True) # CONFIRMED, FALSE_POSITIVE, DISMISSED
    notes = Column(Text, nullable=True)
    
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now())

    detection_result = relationship("DetectionResult", back_populates="judge_review")
    reviewer = relationship("User")
