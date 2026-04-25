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

    # Prepare suspect frames
    for f in sv.frames:
        suspect_frames_data.append(ScrapedFrameMinimal(
            frame_number=f.frame_number,
            file_path=f.file_path,
            phash_value=f.phash_value,
            pdq_hash=f.pdq_hash
        ))

    if det.matched_asset_id:
        asset = db.query(Asset).filter(Asset.id == det.matched_asset_id).first()
        if asset:
            asset_name = asset.asset_name
            asset_owner = asset.owner_company
            
            # Prepare all reference frames for the UI
            for f in asset.frames:
                ref_frames_data.append(AssetFrameMinimal(
                    frame_number=f.frame_number,
                    file_path=f.file_path,
                    phash_value=f.phash_value,
                    pdq_hash=f.pdq_hash
                ))

            # Compute per-frame similarities for graphing
            best_overall_dist = 64
            for s_f in sv.frames:
                max_phash_sim = 0.0
                max_pdq_sim = 0.0
                
                # pHash comparison
                if s_f.phash_value:
                    try:
                        s_h = imagehash.hex_to_hash(s_f.phash_value)
                        for r_f in asset.frames:
                            if r_f.phash_value:
                                r_h = imagehash.hex_to_hash(r_f.phash_value)
                                dist = s_h - r_h
                                sim = max(0.0, 1.0 - (dist / 64.0))
                                if sim > max_phash_sim:
                                    max_phash_sim = sim
                                if dist < best_overall_dist:
                                    best_overall_dist = dist
                                    best_ref_frame_path = r_f.file_path
                    except: pass

                # PDQ comparison
                if s_f.pdq_hash:
                    try:
                        s_v = int(s_f.pdq_hash, 16)
                        for r_f in asset.frames:
                            if r_f.pdq_hash:
                                r_v = int(r_f.pdq_hash, 16)
                                dist = bin(s_v ^ r_v).count('1')
                                sim = max(0.0, 1.0 - (dist / 64.0)) # 64 is the common PDQ threshold
                                if sim > max_pdq_sim:
                                    max_pdq_sim = sim
                    except: pass

                frame_similarities.append(float(round(max_phash_sim, 4)))
                pdq_similarities.append(float(round(max_pdq_sim, 4)))

            # Fallback for best_ref_frame_path
            if not best_ref_frame_path and asset.frames:
                best_ref_frame_path = asset.frames[0].file_path

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
        frames=[f.file_path for f in sv.frames] or sv.frame_paths or [],
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
