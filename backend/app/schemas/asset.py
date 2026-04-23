"""Asset-related Pydantic schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AssetFrame(BaseModel):
    id: int
    frame_number: int
    file_path: str
    phash_value: Optional[str] = None
    pdq_hash: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedFrames(BaseModel):
    frames: list[AssetFrame]
    total: int
    page: int
    limit: int


class AssetOut(BaseModel):
    id: int
    asset_name: str
    owner_company: str
    match_description: Optional[str] = None
    scrap_youtube: bool
    scrap_reddit: bool
    scrap_instagram: bool
    total_frames: int
    status: str
    created_at: datetime
    audio_fp: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AssetRegisterResponse(BaseModel):
    status: str
    asset_id: int
    name: str
