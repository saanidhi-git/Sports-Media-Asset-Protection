"""Pipeline — scan initiation, job status polling, enriched result retrieval."""
import json
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.job_logging import JOB_LOGS_DIR
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
    ExternalPushRequest,
)
from app.services.pipeline.orchestrator import (
    run_pipeline_job, 
    process_external_results, 
    process_raw_external_item, 
    verify_scan_results
)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.post("/external-push-raw", status_code=status.HTTP_202_ACCEPTED)
def push_external_raw(
    background_tasks: BackgroundTasks,
    job_id: int = Form(...),
    api_key: str = Form(...),
    metadata_json: str = Form(...), # Standard fields: platform, title, url, etc.
    frames: list[UploadFile] = File(...),
    audio: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Receives raw frames and audio from local agent. 
    Extraction & fingerprinting happen here on Render.
    """
    if api_key != settings.EXTERNAL_AGENT_KEY:
        raise HTTPException(status_code=403, detail="Invalid external agent API key.")

    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found.")

    try:
        metadata = json.loads(metadata_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid metadata_json.")

    # Read files into memory for background processing
    frame_bytes = [f.file.read() for f in frames]
    audio_bytes = audio.file.read() if audio else None

    # Extraction & fingerprinting can now be sent directly from agent
    job.external_data_received = True
    db.add(job)
    db.commit()

    background_tasks.add_task(
        process_raw_external_item,
        job.id,
        metadata,
        frame_bytes,
        audio_bytes,
    )
    return {"status": "accepted", "job_id": job.id}


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


from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Form, Request, Response

@router.get("/download-agent")
def download_agent(request: Request, job_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Download the local agent script. 
    If job_id is provided, it bundles the target URLs directly into the script.
    """
    # In Docker, the current working directory is /app (backend root)
    agent_path = os.path.join(os.getcwd(), "local_agent.py")
    
    if not os.path.exists(agent_path):
        # Local dev fallback
        agent_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "local_agent.py")
    
    if not os.path.exists(agent_path):
        logger.error(f"Agent file not found at: {agent_path}. CWD: {os.getcwd()}")
        raise HTTPException(status_code=404, detail="local_agent.py not found on server.")

    with open(agent_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. DYNAMIC INJECTION: Base URL
    base_url = str(request.base_url).rstrip("/")
    api_base = f"{base_url}{settings.API_V1_STR}" if "/api/v1" not in base_url else base_url
    content = content.replace(
        'API_BASE_URL = "https://your-app-on-render.com/api/v1"', 
        f'API_BASE_URL = "{api_base}"'
    )

    # 2. DYNAMIC INJECTION: Target Videos
    if job_id:
        videos = db.query(ScrapedVideo).filter(ScrapedVideo.scan_job_id == job_id).all()
        # Convert model objects to simple dicts for JSON embedding
        video_list = []
        for v in videos:
            video_list.append({
                "platform": v.platform,
                "platform_video_id": v.platform_video_id,
                "title": v.title,
                "url": v.url,
                "description": v.description,
                "uploader": v.uploader,
                "like_count": v.like_count,
                "view_count": v.view_count,
                "comments": v.comments or []
            })
        
        # Replace the placeholder in the script with a JSON string wrapped in json.loads()
        json_data = json.dumps(video_list)
        content = content.replace("TARGET_VIDEOS = []", f"TARGET_VIDEOS = json.loads({json.dumps(json_data)})")
        content = content.replace("JOB_ID = 0", f"JOB_ID = {job_id}")

    filename = f"agent_job_{job_id}.py" if job_id else "local_agent.py"

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/jobs/{job_id}/videos")
def get_job_videos(
    job_id: int,
    db: Session = Depends(get_db),
):
    """List discovered videos for a specific job (for local agent to process)."""
    videos = db.query(ScrapedVideo).filter(ScrapedVideo.scan_job_id == job_id).all()
    return [
        {
            "id": v.id,
            "platform": v.platform,
            "platform_video_id": v.platform_video_id,
            "title": v.title,
            "url": v.url,
            "frame_paths": v.frame_paths,
            "uploader": v.uploader
        }
        for v in videos
    ]

@router.post("/jobs/{job_id}/verify")
def trigger_verification(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Manually trigger hashing and matching after frames are pushed."""
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    background_tasks.add_task(verify_scan_results, job_id)
    return {"status": "verification_started"}

@router.post("/external-push", status_code=status.HTTP_202_ACCEPTED)
def push_external_results(
    request: ExternalPushRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Endpoint for local/offline agents to push scraped fingerprints back to the cloud.
    """
    if request.api_key != settings.EXTERNAL_AGENT_KEY:
        raise HTTPException(status_code=403, detail="Invalid external agent API key.")

    job = db.query(ScanJob).filter(ScanJob.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found.")

    # Convert items to dict for orchestrator
    items_dict = [item.model_dump() for item in request.items]

    background_tasks.add_task(
        process_external_results,
        job.id,
        items_dict,
    )
    return {"status": "accepted", "job_id": job.id}


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


from app.services.review.queue import get_human_review_queue, get_review_case, get_user_stats


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns high-level statistics for the user dashboard.
    """
    return get_user_stats(db, current_user.id)


@router.get("/review-queue", response_model=list[EnrichedDetectionResult])
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all detection results tagged as REVIEW or VIOLATED for the current user.
    Uses the dedicated review service.
    """
    return get_human_review_queue(db, current_user.id)


@router.get("/review-queue/{case_id}", response_model=EnrichedDetectionResult)
def get_case_detail(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a specific detection result case detail.
    """
    case = get_review_case(db, case_id, current_user.id)
    if not case:
        raise HTTPException(status_code=404, detail="Review case not found.")
    return case


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
