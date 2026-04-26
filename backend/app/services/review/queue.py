import imagehash
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models.detection_result import DetectionResult
from app.db.models.scraped_video import ScrapedVideo
from app.db.models.scan_job import ScanJob
from app.db.models.asset import Asset
from app.schemas.pipeline import EnrichedDetectionResult, AssetFrameMinimal, ScrapedFrameMinimal

def enrich_detection_result(db: Session, det: DetectionResult) -> EnrichedDetectionResult:
    """
    Enriches a single detection result with suspect video details and matched asset context.
    Includes granular per-frame pHash and PDQ similarities for scatter plotting.
    """
    sv = det.scraped_video
    asset = None
    asset_name = None
    asset_owner = None
    best_ref_frame_path = None
    ref_frames_data = []
    suspect_frames_data = []
    frame_similarities = []
    pdq_similarities = []

    # Prepare suspect frames (sorted by number)
    sorted_suspect_frames = sorted(sv.frames, key=lambda x: x.frame_number)
    for f in sorted_suspect_frames:
        suspect_frames_data.append(ScrapedFrameMinimal(
            frame_number=f.frame_number,
            file_path=f.file_path,
            phash_value=f.phash_value,
            pdq_hash=f.pdq_hash
        ))
    
    # Fallback if frames relationship is empty but frame_paths exists
    if not suspect_frames_data and sv.frame_paths:
        for i, path in enumerate(sv.frame_paths):
            suspect_frames_data.append(ScrapedFrameMinimal(
                frame_number=i,
                file_path=path
            ))

    # Extract frame URLs for the summary list (AFTER FALLBACK)
    all_frame_urls = [f.file_path for f in suspect_frames_data]
        
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Enriching Result {det.id}: Found {len(all_frame_urls)} frame URLs for video {sv.id}")

    return EnrichedDetectionResult(
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
        frames=all_frame_urls,
        suspect_frames=suspect_frames_data,
        matched_asset_id=det.matched_asset_id,
        matched_asset_name=asset_name,
        matched_asset_owner=asset_owner,
        best_ref_frame_path=best_ref_frame_path,
        matched_asset_frames=ref_frames_data,
        frame_similarities=frame_similarities,
        pdq_similarities=pdq_similarities,
        uploader=sv.uploader,
        comments=sv.comments or [],
        like_count=sv.like_count,
        view_count=sv.view_count,
        ai_decision=det.ai_decision,
        ai_reason=det.ai_reason,
        dispatch_status=det.dispatch_status,
        dispatched_at=det.dispatched_at,
        created_at=det.created_at,
    )

def get_human_review_queue(db: Session, user_id: int) -> list[EnrichedDetectionResult]:
    """
    Fetches all detection results that require human intervention.
    """
    rows = (
        db.query(DetectionResult)
        .join(ScrapedVideo, DetectionResult.scraped_video_id == ScrapedVideo.id)
        .join(ScanJob, ScrapedVideo.scan_job_id == ScanJob.id)
        .filter(ScanJob.user_id == user_id)
        .filter(DetectionResult.verdict.in_(["REVIEW", "VIOLATED"]))
        .order_by(DetectionResult.created_at.desc())
        .all()
    )
    return [enrich_detection_result(db, det) for det in rows]

def get_review_case(db: Session, detection_id: int, user_id: int) -> EnrichedDetectionResult:
    """
    Fetches a specific detection result case.
    """
    det = (
        db.query(DetectionResult)
        .join(ScrapedVideo, DetectionResult.scraped_video_id == ScrapedVideo.id)
        .join(ScanJob, ScrapedVideo.scan_job_id == ScanJob.id)
        .filter(DetectionResult.id == detection_id, ScanJob.user_id == user_id)
        .first()
    )
    if not det:
        return None
    return enrich_detection_result(db, det)

def get_user_stats(db: Session, user_id: int) -> dict:
    """
    Returns high-level statistics for the user dashboard.
    """
    total_assets = db.query(Asset).filter(Asset.user_id == user_id).count()
    
    # Counts of detections by verdict
    detections = (
        db.query(DetectionResult.verdict, func.count(DetectionResult.id))
        .join(ScrapedVideo, DetectionResult.scraped_video_id == ScrapedVideo.id)
        .join(ScanJob, ScrapedVideo.scan_job_id == ScanJob.id)
        .filter(ScanJob.user_id == user_id)
        .group_by(DetectionResult.verdict)
        .all()
    )
    
    stats = {
        "total_assets": total_assets,
        "violations_found": 0,
        "pending_reviews": 0,
        "clean_content": 0
    }
    
    for verdict, count in detections:
        if verdict == "VIOLATED":
            stats["violations_found"] = count
        elif verdict == "REVIEW":
            stats["pending_reviews"] = count
        elif verdict == "DROP":
            stats["clean_content"] = count
            
    return stats
