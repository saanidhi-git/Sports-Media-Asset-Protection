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

        logger.info(f"      🔍 Match check against '{asset.asset_name}': Score={score_data['final_score']:.3f} (pHash={p:.2f}, PDQ={pdq:.2f}, Audio={a:.2f}, Meta={m:.2f})")

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
                metadata_score=ai_m_score, # Boost with AI metadata analysis
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

def process_external_results(job_id: int, items: list[dict]):
    """
    Entry point for results pushed by an external local agent.
    """
    import threading
    from app.db.session import SessionLocal
    threading.current_thread().job_id = job_id
    
    db = SessionLocal()
    try:
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if not job:
            logger.error(f"❌ process_external_results: ScanJob {job_id} not found.")
            return

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
        db.close()
        threading.current_thread().job_id = None

def process_raw_external_item(
    job_id: int, 
    metadata: dict, 
    frame_bytes_list: list[bytes], 
    audio_bytes: Optional[bytes] = None
):
    """
    Step 2: Receives raw frames/audio. Stores them on Cloudinary.
    NO HASHING happens here.
    """
    import threading
    from app.db.session import SessionLocal
    threading.current_thread().job_id = job_id
    
    db = SessionLocal()
    try:
        from app.services.storage.cloudinary_client import upload_image
        import tempfile
        import os

        # 1. Find the target record from Discovery
        scraped = db.query(ScrapedVideo).filter(
            ScrapedVideo.scan_job_id == job_id,
            ScrapedVideo.platform_video_id == metadata["platform_video_id"]
        ).first()

        if not scraped:
            scraped = ScrapedVideo(
                scan_job_id=job_id, platform=metadata["platform"],
                platform_video_id=metadata["platform_video_id"],
                title=metadata["title"], url=metadata["url"],
                description=metadata.get("description"),
                uploader=metadata.get("uploader"),
                like_count=metadata.get("like_count"),
                view_count=metadata.get("view_count"),
                comments=metadata.get("comments", [])
            )
            db.add(scraped)
            db.commit()
            db.refresh(scraped)
        else:
            # Update existing record with rich metadata from agent (don't overwrite with None)
            if metadata.get("description"): scraped.description = metadata["description"]
            if metadata.get("uploader"): scraped.uploader = metadata["uploader"]
            if metadata.get("like_count"): scraped.like_count = metadata["like_count"]
            if metadata.get("view_count"): scraped.view_count = metadata["view_count"]
            if metadata.get("comments"): scraped.comments = metadata["comments"]
            db.commit()

        # 2. Store Raw Audio on Cloudinary
        if audio_bytes:
            logger.info(f"   📤 Uploading raw audio for: {scraped.platform_video_id}")
            with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp.flush()
                tmp.close()
                from app.services.storage.cloudinary_client import upload_auto
                audio_url = upload_auto(tmp.name, folder="sports-guardian/raw_audio")
                scraped.audio_url = audio_url
                os.remove(tmp.name)

        # 3. Store raw JPGs on Cloudinary
        frame_urls = []
        logger.info(f"   📤 Uploading {len(frame_bytes_list)} frames for: {scraped.platform_video_id} to Cloudinary")
        for i, b in enumerate(frame_bytes_list):
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(b)
                tmp.flush()
                tmp.close()
                url = upload_image(tmp.name, folder="sports-guardian/scraped_frames")
                if url:
                    logger.info(f"      ✅ Frame {i} uploaded: {url}")
                    frame_urls.append(url)
                else:
                    logger.error(f"      ❌ Frame {i} upload returned NULL secure_url!")
                os.remove(tmp.name)

        if not frame_urls:
            logger.error(f"   ❌ No frames were successfully uploaded to Cloudinary for {scraped.platform_video_id}")
            return

        scraped.frame_paths = frame_urls
        # Clear old frames, add new placeholders linked to the URLs
        db.query(ScrapedFrame).filter(ScrapedFrame.scraped_video_id == scraped.id).delete()
        for i, f_url in enumerate(frame_urls):
            db.add(ScrapedFrame(
                frame_number=i, file_path=f_url,
                scraped_video_id=scraped.id
            ))
        
        db.commit()
        logger.info(f"   💾 Saved {len(frame_urls)} frame URLs to ScrapedFrame table for {scraped.platform_video_id}")

        # Update Job Status
        all_videos = db.query(ScrapedVideo).filter(ScrapedVideo.scan_job_id == job_id).all()
        ready_count = sum(1 for v in all_videos if v.frame_paths and len(v.frame_paths) > 0)
        
        if ready_count >= len(all_videos):
            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if job:
                job.status = "READY_FOR_VERIFICATION"
                db.commit()
                logger.info(f"🎯 SYSTEM READY — All raw data stored for Job {job_id}.")
    except Exception:
        db.rollback()
        logger.error(f"❌ process_raw_external_item failed:\n{traceback.format_exc()}")
    finally:
        db.close()
        threading.current_thread().job_id = None

def verify_scan_results(job_id: int):
    """
    Step 3: CREATE HASHES (pHash, PDQ, Audio) from the raw files 
    that were stored in Step 2, then run similarity comparison.
    """
    import threading
    from app.db.session import SessionLocal
    threading.current_thread().job_id = job_id
    
    db = SessionLocal()
    try:
        from app.services.fingerprint.generator import get_phash, get_pdq, get_audio_fp
        import requests
        import numpy as np
        import cv2
        import tempfile
        import os

        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if not job: return

        job.status = "VERIFYING"
        db.commit()

        logger.info(f"⚙️ CLOUD HASHING & MATCHING STARTED — Job {job_id}")
        
        scraped_videos = db.query(ScrapedVideo).filter(ScrapedVideo.scan_job_id == job_id).all()
        for sv in scraped_videos:
            logger.info(f"──── 🎬 Processing: {sv.title[:60]}")
            
            # 1. Generate Audio Hash on Cloud
            if sv.audio_url:
                logger.info(f"   🎵 Fingerprinting audio on cloud...")
                resp = requests.get(sv.audio_url)
                if resp.status_code == 200:
                    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
                        tmp.write(resp.content)
                        tmp.flush()
                        tmp.close()
                        sv.audio_fp = get_audio_fp(tmp.name)
                        os.remove(tmp.name)
            
            # 2. Generate Visual Hashes (pHash + PDQ) on Cloud
            current_phashes = []
            current_pdq_hashes = []
            logger.info(f"   🎞️ Generating visual hashes for {len(sv.frames)} frames...")
            for i, frame_record in enumerate(sv.frames):
                logger.info(f"      Downloading frame {i}: {frame_record.file_path}")
                resp = requests.get(frame_record.file_path)
                if resp.status_code == 200:
                    nparr = np.frombuffer(resp.content, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if img is not None:
                        ph = get_phash(img)
                        pdq = get_pdq(img)
                        frame_record.phash_value = ph
                        frame_record.pdq_hash = pdq
                        current_phashes.append(ph)
                        current_pdq_hashes.append(pdq)
                        logger.info(f"      ✅ Frame {i} hashed (pHash={ph[:8]}..., PDQ={pdq[:8]}...)")
                    else:
                        logger.error(f"      ❌ Frame {i}: cv2.imdecode failed!")
                else:
                    logger.error(f"      ❌ Frame {i}: Download failed (Status {resp.status_code})!")
            
            db.commit() # Save hashes
            logger.info(f"   💾 Persisted {len(current_phashes)} hashes to DB for {sv.platform_video_id}")

            # 3. AI Analysis & Final Matching
            ai_decision, ai_reason = ai_moderate(sv.title, sv.description or "")
            
            if ai_decision == "DISCUSSION":
                logger.info(f"   ⏭️ Skipping classified as DISCUSSION.")
                sv.status = "SKIPPED_DISCUSSION" # Useful for UI filtering
                db.commit()
                continue

            scraped_text = f"{sv.title} {sv.description or ''}".strip()
            _match_against_assets(
                db, sv, current_phashes, current_pdq_hashes, sv.audio_fp,
                scraped_text=scraped_text, scraped_comments=sv.comments or [],
                ai_decision=ai_decision, ai_reason=ai_reason
            )

        job.status = "COMPLETED"
        job.completed_at = datetime.datetime.utcnow()
        db.commit()
        logger.info(f"✅ ALL VERIFICATIONS COMPLETED.")
    except Exception:
        db.rollback()
        job.status = "FAILED"
        db.commit()
        logger.error(f"❌ Verification failed:\n{traceback.format_exc()}")
    finally:
        db.close()
        threading.current_thread().job_id = None

def run_pipeline_job(
    job_id: int,
    platform_limits: Dict[str, int],
    num_frames_per_video: int = 8,
):
    """
    Phase 1: Discovery only. Finds URLs and lists them for the user.
    """
    import threading
    from app.db.session import SessionLocal
    threading.current_thread().job_id = job_id
    
    db = SessionLocal()
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job: return

    try:
        job.status = "DISCOVERY_ACTIVE"
        db.commit()

        logger.info(f"🔍 PHASE 1: DISCOVERY — Query: '{job.search_query}'")

        from app.services.scraper import youtube as yt_scraper
        from app.services.scraper import instagram as ig_scraper

        # We only do Search API calls here (No Downloading)
        discovered_count = 0
        
        # YouTube Search
        if "youtube" in platform_limits:
            logger.info(f"🔴 Searching YouTube...")
            try:
                items = yt_scraper._api_search(job.search_query, platform_limits["youtube"])
                for item in items:
                    vid = item["id"]["videoId"]
                    db.add(ScrapedVideo(
                        scan_job_id=job.id, platform="youtube", platform_video_id=vid,
                        title=item["snippet"]["title"], description=item["snippet"]["description"],
                        url=f"https://www.youtube.com/watch?v={vid}",
                        uploader=item["snippet"]["channelTitle"]
                    ))
                    discovered_count += 1
            except Exception as e: logger.error(f"YT Search failed: {e}")

        # Instagram Search
        if "instagram" in platform_limits:
            logger.info(f"📷 Searching Instagram...")
            try:
                raw_results = ig_scraper._tavily_search(job.search_query)
                for r in raw_results[:platform_limits["instagram"]]:
                    url = r.get("url", "")
                    if "/reel/" in url or "/p/" in url:
                        vid = url.split("/")[-2]
                        db.add(ScrapedVideo(
                            scan_job_id=job.id, platform="instagram", platform_video_id=vid,
                            title=r.get("title", f"Instagram Reel {vid}"), 
                            description=r.get("content", ""), url=url
                        ))
                        discovered_count += 1
            except Exception as e: logger.error(f"IG Search failed: {e}")

        # Reddit Search
        if "reddit" in platform_limits:
            logger.info(f"🟠 Searching Reddit...")
            try:
                from app.services.scraper import reddit as rd_scraper
                # Reddit search logic (from reddit.py)
                data = rd_scraper._search_page(job.search_query, None)
                children = data.get("data", {}).get("children", [])
                for child in children[:platform_limits["reddit"]]:
                    p = child["data"]
                    if rd_scraper._is_video_post(p):
                        db.add(ScrapedVideo(
                            scan_job_id=job.id, platform="reddit", platform_video_id=p.get("id"),
                            title=p.get("title", "Reddit Video"), description=p.get("selftext", ""),
                            url=f"https://reddit.com{p.get('permalink', '')}",
                            uploader=p.get("author")
                        ))
                        discovered_count += 1
            except Exception as e: logger.error(f"Reddit Search failed: {e}")

        job.status = "WAITING_FOR_LOCAL_AGENT"
        db.commit()
        logger.info(f"✅ DISCOVERY FINISHED: Found {discovered_count} targets. Waiting for Local Agent.")

    except Exception:
        db.rollback()
        job.status = "FAILED"
        db.commit()
        logger.error(f"❌ Discovery failed:\n{traceback.format_exc()}")
    finally:
        db.close()
        threading.current_thread().job_id = None
