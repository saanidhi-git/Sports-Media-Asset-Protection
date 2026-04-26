"""Notice / takedown routes (DMCA generation and dispatch)."""
import os
import requests
import tempfile
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.db.models.detection_result import DetectionResult
from app.schemas.notice import NoticeSend
from app.services.notice.smtp import send_email

router = APIRouter(prefix="/notice", tags=["Notice"])


@router.post("/generate")
def generate_takedown(detection_id: int, _: User = Depends(get_current_user)):
    """Generate a DMCA / platform takedown notice for a flagged detection."""
    # TODO: integrate AI-driven notice generation
    return {"status": "generated", "notice_id": f"NT-{detection_id}"}


@router.post("/send")
def send_notice(
    notice_data: NoticeSend, 
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Dispatch a generated notice via email with optional attachments."""
    temp_files = []
    try:
        # Find the detection result
        detection = db.query(DetectionResult).filter(DetectionResult.id == notice_data.detection_id).first()
        if not detection:
            raise HTTPException(status_code=404, detail="Detection result not found")

        processed_attachments = []
        if notice_data.attachments:
            for path in notice_data.attachments:
                # Handle URLs (Cloudinary)
                if path.startswith("http://") or path.startswith("https://"):
                    try:
                        resp = requests.get(path, timeout=10)
                        if resp.status_code == 200:
                            # Create a temporary file
                            ext = os.path.splitext(path.split("?")[0])[1] or ".jpg"
                            if len(ext) > 5: ext = ".jpg" # Cleanup weird URL extensions
                            
                            fd, temp_path = tempfile.mkstemp(suffix=ext)
                            os.close(fd)
                            with open(temp_path, "wb") as f:
                                f.write(resp.content)
                            
                            processed_attachments.append(temp_path)
                            temp_files.append(temp_path)
                        else:
                            print(f"DEBUG: Failed to download attachment from URL: {path} (Status: {resp.status_code})")
                    except Exception as e:
                        print(f"DEBUG: Error downloading attachment {path}: {e}")
                    continue

                # Handle local paths
                full_path = os.path.join(os.getcwd(), path)
                if not os.path.exists(full_path):
                    # Try relative to 'backend' folder
                    full_path = os.path.join(os.getcwd(), "backend", path)
                
                if os.path.exists(full_path):
                    processed_attachments.append(full_path)
                else:
                    # If it starts with /uploads/ and we are in backend dir, try stripping /
                    alt_path = path.lstrip("/")
                    if os.path.exists(alt_path):
                        processed_attachments.append(os.path.abspath(alt_path))
                    else:
                        print(f"DEBUG: Attachment not found at {path} or backend/{path}")

        send_email(
            email_to=notice_data.recipient_email,
            subject=notice_data.subject,
            html_content=notice_data.content.replace("\n", "<br>"),
            attachments=processed_attachments
        )
        
        # Update database status
        detection.dispatch_status = "DISPATCHED"
        detection.dispatched_at = datetime.now()
        db.add(detection)
        db.commit()
        
        return {
            "status": "dispatched", 
            "recipient": notice_data.recipient_email, 
            "attachments_sent": len(processed_attachments),
            "detection_id": notice_data.detection_id
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
    finally:
        # Cleanup temporary files
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass
