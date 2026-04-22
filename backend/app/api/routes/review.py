from fastapi import APIRouter

router = APIRouter(prefix="/review", tags=["Review"])

@router.get("/queue")
async def get_review_queue():
    # Return list of detections needing human approval
    return {"detections": []}

@router.post("/{detection_id}/approve")
async def approve_detection(detection_id: str):
    return {"status": "approved", "id": detection_id}
