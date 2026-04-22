import os
import json
import uuid
import shutil
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.db.base import Asset, User

router = APIRouter(prefix="/assets", tags=["Assets"])

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/")
async def get_assets(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Fetch all assets registered by the current user.
    """
    assets = db.query(Asset).filter(Asset.user_id == current_user.id).order_by(Asset.created_at.desc()).all()
    return assets

@router.post("/register")
def register_asset(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    asset_name: str = Form(...),
    owner_company: str = Form(...),
    match_description: Optional[str] = Form(None),
    media_to_scrap: str = Form(...), # JSON stringified booleans
    selected_file: UploadFile = File(...),
    scoreboard_file: Optional[UploadFile] = File(None)
):
    try:
        # Check for existing asset with same name to prevent duplicates
        existing_asset = db.query(Asset).filter(
            Asset.asset_name == asset_name, 
            Asset.user_id == current_user.id
        ).first()
        if existing_asset:
            raise HTTPException(status_code=400, detail=f"Asset with name '{asset_name}' already registered.")

        # 1. Parse media_to_scrap
        media_options = json.loads(media_to_scrap)
        
        # 2. Save Media File
        file_ext = os.path.splitext(selected_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        media_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(media_path, "wb") as buffer:
            shutil.copyfileobj(selected_file.file, buffer)
            
        # 3. Save Scoreboard File (if present)
        scoreboard_path = None
        if scoreboard_file:
            sb_ext = os.path.splitext(scoreboard_file.filename)[1]
            sb_filename = f"{uuid.uuid4()}{sb_ext}"
            scoreboard_path = os.path.join(UPLOAD_DIR, sb_filename)
            with open(scoreboard_path, "wb") as buffer:
                shutil.copyfileobj(scoreboard_file.file, buffer)

        # 4. Create Database Entry
        db_obj = Asset(
            asset_name=asset_name,
            owner_company=owner_company,
            match_description=match_description,
            media_file_path=media_path,
            scoreboard_file_path=scoreboard_path,
            scrap_youtube=media_options.get('youtube', False),
            scrap_reddit=media_options.get('reddit', False),
            scrap_instagram=media_options.get('instagram', False),
            user_id=current_user.id,
            status="PENDING"
        )
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        return {
            "status": "success",
            "asset_id": db_obj.id,
            "name": db_obj.asset_name
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error registering asset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to register asset: {str(e)}")
