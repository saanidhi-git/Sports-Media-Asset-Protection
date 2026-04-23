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
from app.services.decision.ai_moderator import ai_moderate
from app.services.scoring.engine import (
    audio_similarity,
    compute_verdict,
    pdq_similarity,
    phash_similarity,
)

logger = logging.getLogger(__name__)


def _match_against_assets(
    db: Session,
    scraped_video: ScrapedVideo,
    suspect_phashes: list[str],
    suspect_pdq_hashes: list[str],
    suspect_audio_fp: str | None,
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

        score_data = compute_verdict(p, pdq, a)

        if best_score_data is None or score_data["final_score"] > best_score_data["final_score"]:
            best_score_data = score_data
            best_asset_id   = asset.id

    if best_score_data is None:
        best_score_data = {
            "phash_score": 0.0, "pdq_score": 0.0, "audio_score": 0.0,
            "final_score": 0.0, "verdict": "DROP",
        }

    detection = DetectionResult(
        scraped_video_id = scraped_video.id,
        matched_asset_id = best_asset_id if best_score_data["verdict"] in ("FLAG", "REVIEW") else None,
        phash_score      = best_score_data["phash_score"],
        pdq_score        = best_score_data["pdq_score"],
        audio_score      = best_score_data["audio_score"],
        final_score      = best_score_data["final_score"],
        verdict          = best_score_data["verdict"],
        ai_decision      = ai_decision,
        ai_reason        = ai_reason,
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)

    logger.info(
        f"⚖️ [3/4] DetectionResult {detection.id}: verdict={detection.verdict} "
        f"score={detection.final_score:.3f} (video={scraped_video.id})"
    )
    return detection


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
                )
            except Exception as e:
                logger.error(f"❌ Scraper {platform} failed: {e}", exc_info=True)
                continue

            for item in items:
                logger.info(f"──── 🎬 Processing: {item['title'][:60]}")
                
                # ── Agent 6: AI Moderation ─────────────────────────────────
                ai_decision, ai_reason = ai_moderate(item["title"])
                logger.info(f"   🤖 [AI] {ai_decision} | {ai_reason}")
                
                if ai_decision == "DISCUSSION":
                    logger.info(f"   ⏭️ Skipping classified as DISCUSSION.")
                    continue

                # Persist the scraped video record
                scraped = ScrapedVideo(
                    scan_job_id       = job.id,
                    platform          = item["platform"],
                    platform_video_id = item["platform_video_id"],
                    title             = item["title"],
                    url               = item["url"],
                    frame_paths       = item.get("frame_paths", []),
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
                logger.info(f"   🔍 [3/4] Running Piracy Scan (pHash + PDQ + Audio)...")
                _match_against_assets(
                    db,
                    scraped,
                    phashes,
                    pdq_hashes,
                    item.get("audio_fp"),
                    ai_decision=ai_decision,
                    ai_reason=ai_reason,
                )

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
