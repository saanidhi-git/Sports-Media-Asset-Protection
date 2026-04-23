"""Review / Judge Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

VALID_DECISIONS = {"CONFIRMED", "FALSE_POSITIVE", "DISMISSED"}


class ReviewDecision(BaseModel):
    decision: str
    notes: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in VALID_DECISIONS:
            raise ValueError(f"Must be one of {VALID_DECISIONS}")
        return v


class JudgeReviewOut(BaseModel):
    id: int
    detection_result_id: int
    reviewer_id: Optional[int] = None
    decision: str
    notes: Optional[str] = None
    reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)
