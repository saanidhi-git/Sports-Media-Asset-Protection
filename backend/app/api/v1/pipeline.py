"""Pipeline — scan initiation, job status polling, enriched result retrieval."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.asset import Asset
from app.db.models.detection_result import DetectionResult
from app.db.models.scan_job import ScanJob
from app.db.models.scraped_video import ScrapedVideo
from app.db.models.user import User
from app.schemas.pipeline import (
    DetectionResultOut,
    EnrichedDetectionResult,
    ScanJobOut,
    ScanRequest,
)
from app.services.pipeline.orchestrator import run_pipeline_job
import os
from app.core.job_logging import JOB_LOGS_DIR

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.post("/scan", response_model=ScanJobOut, status_code=status.HTTP_202_ACCEPTED)
def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initiate a scan job. Returns 202 immediately; pipeline runs in background."""
    platform_limits = request.active_platforms()
    if not platform_limits:
        raise HTTPException(status_code=400, detail="Enable at least one platform (set limit > 0).")

    job = ScanJob(
        user_id=current_user.id,
        search_query=request.search_query,
        platforms=list(platform_limits.keys()),
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        run_pipeline_job,
        job.id,
        platform_limits,
        request.num_frames_per_video,
    )
    return job


@router.get("/jobs", response_model=list[ScanJobOut])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all scan jobs belonging to the current user."""
    return (
        db.query(ScanJob)
        .filter(ScanJob.user_id == current_user.id)
        .order_by(ScanJob.created_at.desc())
        .all()
    )


@router.get("/jobs/{job_id}", response_model=ScanJobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll a specific job's status (for frontend progress tracking)."""
    job = db.query(ScanJob).filter(ScanJob.id == job_id, ScanJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found.")
    return job


@router.get("/results/{job_id}", response_model=list[EnrichedDetectionResult])
def get_enriched_results(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns fully enriched detection results for a given job.
    Each result includes the scraped video metadata and matched asset name.
    """
    job = db.query(ScanJob).filter(ScanJob.id == job_id, ScanJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found.")

    rows = (
        db.query(DetectionResult)
        .join(ScrapedVideo, DetectionResult.scraped_video_id == ScrapedVideo.id)
        .filter(ScrapedVideo.scan_job_id == job_id)
        .order_by(DetectionResult.final_score.desc())
        .all()
    )

    enriched = []
    for det in rows:
        sv = det.scraped_video
        asset_name = None
        if det.matched_asset_id:
            asset = db.query(Asset).filter(Asset.id == det.matched_asset_id).first()
            asset_name = asset.asset_name if asset else None

        # Fetch frame paths from the new ScrapedFrame table
        frame_paths = [f.file_path for f in sv.frames]
        if not frame_paths:
            # Fallback to legacy JSON column if table is empty
            frame_paths = sv.frame_paths or []

        enriched.append(EnrichedDetectionResult(
            id=det.id,
            verdict=det.verdict,
            phash_score=det.phash_score,
            pdq_score=det.pdq_score,
            audio_score=det.audio_score,
            metadata_score=det.metadata_score,
            final_score=det.final_score,
            platform=sv.platform,
            video_title=sv.title,
            video_url=sv.url,
            platform_video_id=sv.platform_video_id,
            frames=frame_paths,
            matched_asset_id=det.matched_asset_id,
            matched_asset_name=asset_name,
            uploader=sv.uploader,
            comments=sv.comments or [],
            like_count=sv.like_count,
            view_count=sv.view_count,
            ai_decision=det.ai_decision,
            ai_reason=det.ai_reason,
            created_at=det.created_at,
        ))
    return enriched


@router.get("/jobs/{job_id}/logs", response_model=list[str])
def get_job_logs(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the minute-by-minute live logs for a specific job.
    """
    job = db.query(ScanJob).filter(ScanJob.id == job_id, ScanJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found.")
        
    log_path = os.path.join(JOB_LOGS_DIR, f"job_{job_id}.log")
    if not os.path.exists(log_path):
        return []
        
    with open(log_path, "r", encoding="utf-8") as f:
        # Filter out empty lines
        lines = [line.strip() for line in f.readlines() if line.strip()]
        
    return lines
