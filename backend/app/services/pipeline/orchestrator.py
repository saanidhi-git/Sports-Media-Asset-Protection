"""
Pipeline Orchestrator — ties scraper -> fingerprints -> scoring -> DB persistence.
"""
import datetime
import logging
import traceback
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.detection_result import DetectionResult
from app.db.models.scan_job import ScanJob
from app.db.models.scraped_video import ScrapedVideo
from app.db.models.scraped_frame import ScrapedFrame
from app.services.scoring.engine import (
    audio_similarity,
    compute_verdict,
    pdq_similarity,
    phash_similarity,
    metadata_similarity,
)
from app.services.decision.ai_moderator import ai_moderate, ai_deep_analysis

logger = logging.getLogger(__name__)

def _make_score_fn():
    """
    Returns a closure that computes a rolling piracy similarity score against
    all COMPLETED assets in the DB. Used as the early_exit_score_fn callback.
    """
    from app.db.session import SessionLocal
    from app.db.models.asset import Asset
    from app.services.scoring.engine import phash_similarity, pdq_similarity

    def score_fn(phashes: list[str], pdq_hashes: list[str]) -> float:
        db = SessionLocal()
        best = 0.0
        try:
            for asset in db.query(Asset).filter(Asset.status == "COMPLETED").yield_per(100):
                ref_ph  = [f.phash_value for f in asset.frames if f.phash_value]
                ref_pdq = [f.pdq_hash   for f in asset.frames if f.pdq_hash]
                p   = phash_similarity(phashes, ref_ph)
                pdq = pdq_similarity(pdq_hashes, ref_pdq)
                combined = (p * 0.5) + (pdq * 0.5)
                if combined > best:
                    best = combined
        finally:
            db.close()
        return best

    return score_fn

def _match_against_assets(
    db: Session,
    scraped_video: ScrapedVideo,
    suspect_phashes: list[str],
    suspect_pdq_hashes: list[str],
    suspect_audio_fp: str | None,
    scraped_text: str = "",
    scraped_comments: list[dict] = [],
    ai_decision: Optional[str] = None,
    ai_reason: Optional[str] = None,
) -> DetectionResult:
    """
    Streams DB assets in batches of 100 (memory-safe), runs similarity against
    each, and persists the best DetectionResult.
    """
    best_score_data = None
    best_asset_id   = None

    # yield_per avoids loading entire assets table into RAM
    for asset in db.query(Asset).filter(Asset.status == "COMPLETED").yield_per(100):
        ref_phashes    = [f.phash_value for f in asset.frames if f.phash_value]
        ref_pdq_hashes = [f.pdq_hash   for f in asset.frames if f.pdq_hash]
        ref_audio_fp   = asset.audio_fp

        p   = phash_similarity(suspect_phashes, ref_phashes)
        pdq = pdq_similarity(suspect_pdq_hashes, ref_pdq_hashes)
        a   = audio_similarity(suspect_audio_fp, ref_audio_fp)
        
        # Fast metadata overlap for candidate selection
        m = metadata_similarity(scraped_text, asset.match_description or "")
        
        score_data = compute_verdict(
            p, pdq, a, 
            metadata_score=m, 
            ai_match=(ai_decision == "HIGHLIGHT")
        )

        logger.info(f"      🔍 Match check against '{asset.asset_name}': Score={score_data['final_score']:.3f} (pHash={p:.2f}, PDQ={pdq:.2f}, Meta={m:.2f})")

        if best_score_data is None or score_data["final_score"] > best_score_data["final_score"]:
            best_score_data = score_data
            best_asset_id   = asset.id

    if best_score_data is None:
        best_score_data = {
            "phash_score": 0.0, "pdq_score": 0.0, "audio_score": 0.0,
            "metadata_score": 0.0, "final_score": 0.0, "verdict": "DROP",
        }

    # ── PHASE 4: AI Deep Contextual Analysis ──
    # Only perform deep analysis if we found a potential match candidate
    final_ai_decision = ai_decision
    final_ai_reason = ai_reason
    
    if best_asset_id and best_score_data["verdict"] in ("FLAG", "REVIEW"):
        best_asset = db.query(Asset).filter(Asset.id == best_asset_id).first()
        if best_asset:
            logger.info(f"   🤖 [AI] Performing Deep Analysis against Asset: {best_asset.asset_name}...")
            ai_m_score, ai_m_reason = ai_deep_analysis(
                scraped_title=scraped_video.title,
                scraped_desc=scraped_video.description or "",
                scraped_comments=scraped_comments,
                asset_name=best_asset.asset_name,
                asset_desc=best_asset.match_description or "",
                asset_owner=best_asset.owner_company
            )
            
            # Update the detection with the high-fidelity AI feedback
            # We use the AI score to refine the metadata component of the final score
            is_ai_match = (ai_m_score > 0.7)
            best_score_data = compute_verdict(
                phash_score=best_score_data["phash_score"],
                pdq_score=best_score_data["pdq_score"],
                audio_score=best_score_data["audio_score"],
                metadata_score=ai_m_score,
                ai_match=is_ai_match
            )
            final_ai_reason = ai_m_reason
            final_ai_decision = "MATCH" if is_ai_match else "REVIEW"

    detection = DetectionResult(
        scraped_video_id = scraped_video.id,
        matched_asset_id = best_asset_id if best_score_data["verdict"] in ("FLAG", "REVIEW", "VIOLATED") else None,
        phash_score      = best_score_data["phash_score"],
        pdq_score        = best_score_data["pdq_score"],
        audio_score      = best_score_data["audio_score"],
        metadata_score   = best_score_data["metadata_score"],
        final_score      = best_score_data["final_score"],
        verdict          = best_score_data["verdict"],
        ai_decision      = final_ai_decision,
        ai_reason        = final_ai_reason,
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)

    logger.info(
        f"⚖️ [3/4] DetectionResult {detection.id}: verdict={detection.verdict} "
        f"score={detection.final_score:.3f} (video={scraped_video.id})"
    )
    return detection


import io
from PIL import Image
import numpy as np
import cv2

def process_raw_external_item(
    db: Session, 
    job_id: int, 
    metadata: dict, 
    frame_bytes_list: list[bytes], 
    audio_bytes: Optional[bytes] = None
):
    """
    Handles raw bytes from a local agent. Generates fingerprints ON THE CLOUD
    and then proceeds with the normal pipeline.
    """
    import threading
    threading.current_thread().job_id = job_id
    
    from app.services.fingerprint.generator import get_phash, get_pdq, get_audio_fp
    from app.services.storage.cloudinary_client import upload_image
    import tempfile
    import os

    logger.info(f"📥 EXTERNAL RAW DATA RECEIVED — Starting cloud processing for Job {job_id}")
    logger.info(f"   (Extraction handled by Edge Node / Local Agent)")
    logger.info(f"──── 🎬 Processing: {metadata['title'][:60]}")

    phashes = []
    pdq_hashes = []
    frame_urls = []

    # 1. Process Frames: Hash & Upload
    logger.info(f"   🎞️ Generating pHash & PDQ for {len(frame_bytes_list)} frames on cloud...")
    for i, b in enumerate(frame_bytes_list):
        # Convert bytes to cv2 frame for our existing hashing utils
        nparr = np.frombuffer(b, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is not None:
            phashes.append(get_phash(frame))
            pdq_hashes.append(get_pdq(frame))
            
            # Temporary file for Cloudinary upload
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                cv2.imwrite(tmp.name, frame)
                url = upload_image(tmp.name, folder="sports-guardian/scraped_frames")
                frame_urls.append(url)
                os.remove(tmp.name)

    # 2. Process Audio
    final_audio_fp = None
    if audio_bytes:
        logger.info(f"   🎵 Generating Audio Fingerprint (ChromaPrint) on cloud...")
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            final_audio_fp = get_audio_fp(tmp.name)
            os.remove(tmp.name)

    # 3. Use the existing item processor logic
    item_for_pipeline = {
        **metadata,
        "phashes": phashes,
        "pdq_hashes": pdq_hashes,
        "frame_paths": frame_urls,
        "audio_fp": final_audio_fp,
    }
    
    process_scraped_item(db, job_id, item_for_pipeline)

    # 4. Mark job as completed
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if job:
        job.status = "COMPLETED"
        job.completed_at = datetime.datetime.utcnow()
        db.commit()
        logger.info(f"✅ EXTERNAL RAW PUSH COMPLETED for Job {job_id}")

def process_scraped_item(db: Session, job_id: int, item: dict):
    """
    Common logic to persist a scraped item, extract frames/hashes, 
    run AI moderation, and match against assets.
    """
    logger.info(f"──── 🎬 Processing: {item['title'][:60]}")
    
    # ── AI Moderation ─────────────────────────────────
    ai_decision, ai_reason = ai_moderate(item["title"], item.get("description", ""))
    logger.info(f"   🤖 [AI] {ai_decision} | {ai_reason}")
    
    if ai_decision == "DISCUSSION":
        logger.info(f"   ⏭️ Skipping classified as DISCUSSION.")
        return

    # Persist the scraped video record
    scraped = ScrapedVideo(
        scan_job_id       = job_id,
        platform          = item["platform"],
        platform_video_id = item["platform_video_id"],
        title             = item["title"],
        description       = item.get("description", ""),
        url               = item["url"],
        frame_paths       = item.get("frame_paths", []),
        uploader          = item.get("uploader"),
        like_count        = item.get("like_count"),
        view_count        = item.get("view_count"),
        comments          = item.get("comments", []),
    )
    db.add(scraped)
    db.commit()
    db.refresh(scraped)

    # Persist the frames and their hashes to ScrapedFrame table
    phashes = item.get("phashes", [])
    pdq_hashes = item.get("pdq_hashes", [])
    frame_paths = item.get("frame_paths", [])

    logger.info(f"   🎞 [2/4] Saving {len(frame_paths)} extracted frames...")
    for i, f_path in enumerate(frame_paths):
        db.add(ScrapedFrame(
            frame_number=i,
            file_path=f_path,
            phash_value=phashes[i] if i < len(phashes) else None,
            pdq_hash=pdq_hashes[i] if i < len(pdq_hashes) else None,
            scraped_video_id=scraped.id
        ))
    db.commit()

    # Match against all registered assets
    logger.info(f"   🔍 [3/4] Running Piracy Scan (pHash + PDQ + Audio + Meta)...")
    
    # Build scraped_text for metadata matching
    scraped_text = f"{item['title']} {item.get('description', '')}".strip()
    
    _match_against_assets(
        db,
        scraped,
        phashes,
        pdq_hashes,
        item.get("audio_fp"),
        scraped_text=scraped_text,
        scraped_comments=item.get("comments", []),
        ai_decision=ai_decision,
        ai_reason=ai_reason,
    )

def process_external_results(db: Session, job_id: int, items: list[dict]):
    """
    Entry point for results pushed by an external local agent.
    """
    import threading
    threading.current_thread().job_id = job_id
    
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job:
        logger.error(f"❌ process_external_results: ScanJob {job_id} not found.")
        return

    try:
        job.status = "PROCESSING"
        db.commit()

        logger.info(f"🚀 EXTERNAL PUSH RECEIVED — Processing {len(items)} items for Query: '{job.search_query}'")

        for item in items:
            process_scraped_item(db, job_id, item)

        job.status       = "COMPLETED"
        job.completed_at = datetime.datetime.utcnow()
        db.commit()
        logger.info(f"✅ EXTERNAL PUSH COMPLETED.")
    except Exception:
        db.rollback()
        job.status = "FAILED"
        db.commit()
        logger.error(f"❌ External processing failed:\n{traceback.format_exc()}")
    finally:
        threading.current_thread().job_id = None


def run_pipeline_job(
    job_id: int,
    platform_limits: Dict[str, int],
    num_frames_per_video: int = 8,
):
    """
    Background entry-point called by FastAPI BackgroundTasks.
    Accepts per-platform limits: {"youtube": 3, "instagram": 2, "reddit": 4}
    """
    import threading
    from app.db.session import SessionLocal
    threading.current_thread().job_id = job_id
    
    db = SessionLocal()
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job:
        logger.error(f"❌ run_pipeline_job: ScanJob {job_id} not found.")
        db.close()
        threading.current_thread().job_id = None
        return

    try:
        job.status = "PROCESSING"
        db.commit()

        logger.info(f"🚀 SCAN OPERATION STARTED — Query: '{job.search_query}'")
        logger.info(f"   Platforms: {', '.join([f'{k}({v})' for k,v in platform_limits.items()])}")

        # Import scrapers here (lazy) so missing optional deps don't crash startup
        from app.services.scraper import youtube as yt_scraper
        from app.services.scraper import instagram as ig_scraper
        from app.services.scraper import reddit as rd_scraper

        scraper_map = {
            "youtube":   yt_scraper,
            "instagram": ig_scraper,
            "reddit":    rd_scraper,
        }

        for platform, limit in platform_limits.items():
            scraper = scraper_map.get(platform)
            if not scraper:
                logger.warning(f"⚠️ Unknown platform: {platform}")
                continue

            icon = {"youtube": "🔴", "instagram": "📷", "reddit": "🟠"}.get(platform, "📹")
            logger.info(f"══════════════════════════════════════════════════")
            logger.info(f"{icon} SCRAPING {platform.upper()} — limit={limit}")
            logger.info(f"══════════════════════════════════════════════════")
            
            try:
                items = scraper.scrape_and_fingerprint(
                    job.search_query,
                    limit=limit,
                    num_frames=num_frames_per_video,
                    early_exit_score_fn=_make_score_fn(),
                )
            except Exception as e:
                logger.error(f"❌ Scraper {platform} failed: {e}", exc_info=True)
                continue

            for item in items:
                process_scraped_item(db, job_id, item)

        job.status       = "COMPLETED"
        job.completed_at = datetime.datetime.utcnow()
        db.commit()
        logger.info(f"✅ SCAN OPERATION COMPLETED.")

    except Exception:
        db.rollback()
        job.status = "FAILED"
        db.commit()
        logger.error(f"❌ ScanJob {job_id} failed:\n{traceback.format_exc()}")
    finally:
        db.close()
        threading.current_thread().job_id = None
