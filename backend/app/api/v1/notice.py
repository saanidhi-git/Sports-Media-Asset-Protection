"""Notice / takedown routes (DMCA generation and dispatch stub)."""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.models.user import User

router = APIRouter(prefix="/notice", tags=["Notice"])


@router.post("/generate")
def generate_takedown(detection_id: int, _: User = Depends(get_current_user)):
    """Generate a DMCA / platform takedown notice for a flagged detection."""
    # TODO: integrate AI-driven notice generation
    return {"status": "generated", "notice_id": f"NT-{detection_id}"}


@router.post("/send")
def send_notice(notice_id: str, _: User = Depends(get_current_user)):
    """Dispatch a generated notice to YouTube / Meta / etc."""
    # TODO: integrate platform APIs for sending
    return {"status": "dispatched", "notice_id": notice_id}
