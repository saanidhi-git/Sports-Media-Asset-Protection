"""Judge review queue routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.detection_result import DetectionResult
from app.db.models.judge_review import JudgeReview
from app.db.models.scan_job import ScanJob
from app.db.models.scraped_video import ScrapedVideo
from app.db.models.user import User
from app.schemas.pipeline import DetectionResultOut
from app.schemas.review import JudgeReviewOut, ReviewDecision

router = APIRouter(prefix="/review", tags=["Review"])


@router.get("/queue", response_model=list[DetectionResultOut])
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all FLAG/REVIEW detections with no judge decision yet."""
    return (
        db.query(DetectionResult)
        .join(ScrapedVideo, DetectionResult.scraped_video_id == ScrapedVideo.id)
        .join(ScanJob,      ScrapedVideo.scan_job_id == ScanJob.id)
        .filter(
            ScanJob.user_id == current_user.id,
            DetectionResult.verdict.in_(["FLAG", "REVIEW"]),
            DetectionResult.judge_review == None,  # noqa: E711
        )
        .order_by(DetectionResult.final_score.desc())
        .all()
    )


@router.post("/{detection_id}/decide", response_model=JudgeReviewOut, status_code=status.HTTP_201_CREATED)
def submit_decision(
    detection_id: int,
    body: ReviewDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a human judge decision for a detection.
    Stored immutably — the original AI verdict is never overwritten.
    """
    detection = (
        db.query(DetectionResult)
        .join(ScrapedVideo, DetectionResult.scraped_video_id == ScrapedVideo.id)
        .join(ScanJob,      ScrapedVideo.scan_job_id == ScanJob.id)
        .filter(DetectionResult.id == detection_id, ScanJob.user_id == current_user.id)
        .first()
    )
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found.")
    if detection.judge_review:
        raise HTTPException(status_code=409, detail="Review decision already exists.")

    review = JudgeReview(
        detection_result_id=detection.id,
        reviewer_id=current_user.id,
        decision=body.decision,
        notes=body.notes,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
