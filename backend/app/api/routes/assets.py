from fastapi import APIRouter, UploadFile, File, Form, Depends
from typing import List, Optional
import json

router = APIRouter(prefix="/assets", tags=["Assets"])

@router.post("/register")
async def register_asset(
    asset_name: str = Form(...),
    owner_company: str = Form(...),
    media_to_scrap: str = Form(...), # JSON stringified booleans
    selected_file: UploadFile = File(...),
    scoreboard_file: Optional[UploadFile] = File(None)
):
    # Parse media_to_scrap from JSON string to dict
    media_options = json.loads(media_to_scrap)
    
    # Store files (simulated for now)
    # 1. Save media file (video/image)
    # 2. Save scoreboard file (if present)
    # 3. Create database entry
    
    return {
        "status": "success",
        "asset_id": "ASSET-01",
        "name": asset_name,
        "owner": owner_company,
        "media_options": media_options,
        "file_name": selected_file.filename,
        "scoreboard_file": scoreboard_file.filename if scoreboard_file else None
    }
