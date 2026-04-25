"""Pipeline + Detection Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class ScanRequest(BaseModel):
    """Per-platform limits. Set a platform's limit to 0 to skip it."""
    search_query: str
    youtube_limit: int = 0
    instagram_limit: int = 0
    reddit_limit: int = 0
    num_frames_per_video: int = 8

    @field_validator("youtube_limit", "instagram_limit", "reddit_limit")
    @classmethod
    def validate_limits(cls, v: int) -> int:
        if v < 0 or v > 50:
            raise ValueError("Limit must be between 0 and 50.")
        return v

    def active_platforms(self) -> dict[str, int]:
        """Returns {platform_name: limit} for all enabled platforms."""
        m: dict[str, int] = {}
        if self.youtube_limit > 0:
            m["youtube"] = self.youtube_limit
        if self.instagram_limit > 0:
            m["instagram"] = self.instagram_limit
        if self.reddit_limit > 0:
            m["reddit"] = self.reddit_limit
        return m


class ScanJobOut(BaseModel):
    id: int
    search_query: str
    platforms: list[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DetectionResultOut(BaseModel):
    id: int
    scraped_video_id: int
    matched_asset_id: Optional[int] = None
    phash_score: float
    pdq_score: float
    audio_score: float
    metadata_score: float
    final_score: float
    verdict: str
    ai_decision: Optional[str] = None
    ai_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetFrameMinimal(BaseModel):
    frame_number: int
    file_path: str
    phash_value: Optional[str] = None
    pdq_hash: Optional[str] = None

class ScrapedFrameMinimal(BaseModel):
    frame_number: int
    file_path: str
    phash_value: Optional[str] = None
    pdq_hash: Optional[str] = None

class EnrichedDetectionResult(BaseModel):
    """Detection result joined with ScrapedVideo + matched Asset info for the UI."""
    id: int
    verdict: str
    phash_score: float
    pdq_score: float
    audio_score: float
    metadata_score: float
    final_score: float
    # Scraped video info
    platform: str
    video_title: str
    video_url: str
    platform_video_id: str
    frames: list[str] = [] # Legacy list of paths
    suspect_frames: list[ScrapedFrameMinimal] = []
    # Matched asset info
    matched_asset_id: Optional[int] = None
    matched_asset_name: Optional[str] = None
    matched_asset_owner: Optional[str] = None
    best_ref_frame_path: Optional[str] = None
    matched_asset_frames: list[AssetFrameMinimal] = []
    # Analysis
    frame_similarities: list[float] = [] # Per-frame pHash similarity for graphing
    pdq_similarities: list[float] = []   # Per-frame PDQ similarity for graphing
    uploader: Optional[str] = None
    comments: list[dict] = []
    like_count: Optional[int] = None
    view_count: Optional[int] = None
    # AI Moderation info
    ai_decision: Optional[str] = None
    ai_reason: Optional[str] = None
    # Dispatch info
    dispatch_status: str = "PENDING"
    dispatched_at: Optional[datetime] = None
    
    created_at: datetime
