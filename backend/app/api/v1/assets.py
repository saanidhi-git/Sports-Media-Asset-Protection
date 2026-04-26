"""Asset registration and retrieval routes."""
import json
import os
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.asset import Asset
from app.db.models.asset_frame import AssetFrame
from app.db.models.user import User
from app.schemas.asset import AssetOut, AssetRegisterResponse, PaginatedFrames
from app.services.pipeline.processor import extract_frames
from app.services.storage.cloudinary_client import upload_video, upload_image, upload_auto, delete_asset_by_url

router   = APIRouter(prefix="/assets", tags=["Assets"])
# Use /tmp for Render compatibility, or local uploads/temp for Windows dev
TEMP_DIR = "/tmp/sg_uploads" if os.name != 'nt' else "uploads/temp"
os.makedirs(TEMP_DIR, exist_ok=True)


@router.get("/", response_model=list[AssetOut])
def list_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all assets belonging to the current user."""
    return (
        db.query(Asset)
        .filter(Asset.user_id == current_user.id)
        .order_by(Asset.created_at.desc())
        .all()
    )


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return asset


@router.get("/{asset_id}/frames", response_model=PaginatedFrames)
def get_asset_frames(
    asset_id: int,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    offset = (page - 1) * limit
    frames = (
        db.query(AssetFrame)
        .filter(AssetFrame.asset_id == asset_id)
        .order_by(AssetFrame.frame_number)
        .offset(offset).limit(limit)
        .all()
    )
    total = db.query(AssetFrame).filter(AssetFrame.asset_id == asset_id).count()
    return {"frames": frames, "total": total, "page": page, "limit": limit}


@router.post("/register", response_model=AssetRegisterResponse, status_code=status.HTTP_202_ACCEPTED)
def register_asset(
    background_tasks: BackgroundTasks,
    asset_name: str          = Form(...),
    owner_company: str       = Form(...),
    match_description: Optional[str] = Form(None),
    media_to_scrap: str      = Form(...),  # JSON: {"youtube":true, "reddit":false, ...}
    num_frames: int          = Form(50),
    selected_file: UploadFile = File(...),
    scoreboard_file: Optional[UploadFile] = File(None),
    db: Session              = Depends(get_db),
    current_user: User       = Depends(get_current_user),
):
    """
    Upload an official asset video. Returns 202; fingerprinting runs in background.
    """
    if db.query(Asset).filter(Asset.asset_name == asset_name, Asset.user_id == current_user.id).first():
        raise HTTPException(status_code=400, detail=f"Asset '{asset_name}' already registered.")

    try:
        media_options = json.loads(media_to_scrap)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=422, detail="media_to_scrap must be valid JSON.")

    # Save uploaded video temporarily for local processing
    ext = os.path.splitext(selected_file.filename or "")[1]
    temp_video_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}{ext}")
    with open(temp_video_path, "wb") as buf:
        shutil.copyfileobj(selected_file.file, buf)

    # OPTIMIZATION: We skip uploading the 63MB video to Cloudinary.
    # We will only upload the extracted frames during the background task.
    media_url = f"local_ephemeral://{selected_file.filename}"

    # Optionally save and upload scoreboard image/doc
    scoreboard_url: Optional[str] = None
    if scoreboard_file:
        sb_ext = os.path.splitext(scoreboard_file.filename or "")[1]
        temp_sb_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}{sb_ext}")
        with open(temp_sb_path, "wb") as buf:
            shutil.copyfileobj(scoreboard_file.file, buf)
        try:
            # Handle non-image scoreboards
            scoreboard_url = upload_auto(temp_sb_path, folder="sports-guardian/scoreboards")
        finally:
            if os.path.exists(temp_sb_path):
                os.remove(temp_sb_path)

    asset = Asset(
        asset_name=asset_name,
        owner_company=owner_company,
        match_description=match_description,
        media_file_path=media_url,
        scoreboard_file_path=scoreboard_url,
        scrap_youtube=media_options.get("youtube", False),
        scrap_reddit=media_options.get("reddit", False),
        scrap_instagram=media_options.get("instagram", False),
        total_frames=num_frames,
        user_id=current_user.id,
        status="PROCESSING",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Pass the local temp path for processing, it will be deleted by the processor
    background_tasks.add_task(extract_frames, db, asset.id, num_frames, temp_video_path)

    return {"status": "processing", "asset_id": asset.id, "name": asset.asset_name}


def cleanup_cloudinary_assets(urls: list[str]):
    """Background task to remove files from Cloudinary."""
    for url in urls:
        if url:
            delete_asset_by_url(url)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    
    # Collect all URLs to delete from Cloudinary
    urls_to_delete = [asset.media_file_path, asset.scoreboard_file_path]
    for frame in asset.frames:
        urls_to_delete.append(frame.file_path)
    
    # Delete from DB (cascades to frames, detections, reviews due to model config)
    db.delete(asset)
    db.commit()

    # Trigger background cleanup of physical files
    background_tasks.add_task(cleanup_cloudinary_assets, urls_to_delete)
