import cv2
import gc
import logging
import os
import shutil
import uuid

from sqlalchemy.orm import Session

from app.db.models.asset import Asset
from app.db.models.asset_frame import AssetFrame
from app.services.fingerprint.generator import get_phash, get_pdq, get_audio_fp

logger = logging.getLogger(__name__)


def extract_frames(db: Session, asset_id: int, num_frames: int):
    """
    Background task: extracts evenly-spaced frames from a registered asset video,
    computes pHash + PDQ per-frame and audio fingerprint for the whole file,
    and persists all embeddings to the database.

    Production guarantees:
      - try/except/finally always sets asset.status so it never hangs in PROCESSING.
      - cv2.VideoCapture is always released via finally.
      - Corrupted frames are skipped, not fatal.
      - PIL/numpy intermediate objects are explicitly freed (gc) to prevent leaks.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        logger.error(f"extract_frames: Asset {asset_id} not found.")
        return

    video_path = asset.media_file_path
    if not os.path.exists(video_path):
        logger.error(f"extract_frames: Video not found at {video_path}")
        asset.status = "FAILED"
        db.commit()
        return

    # Frames are stored alongside the uploaded video
    frames_dir = os.path.join(os.path.dirname(video_path), "frames")
    os.makedirs(frames_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    extracted_count = 0

    try:
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_video_frames <= 0:
            raise ValueError(f"Could not read frame count from {video_path}")

        step = max(1, total_video_frames // num_frames)

        for i in range(num_frames):
            frame_idx = i * step
            if frame_idx >= total_video_frames:
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Frame {i} (idx {frame_idx}) could not be read — skipping.")
                continue

            # --- Fingerprinting (each function handles its own errors) ---
            phash = get_phash(frame)
            pdq   = get_pdq(frame)

            # --- Persist frame to disk ---
            frame_filename = f"frame_{i:04d}_{uuid.uuid4().hex[:8]}.jpg"
            frame_path = os.path.join(frames_dir, frame_filename)
            cv2.imwrite(frame_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

            # Free the raw frame array immediately
            del frame
            gc.collect()

            # --- Persist to DB ---
            db.add(AssetFrame(
                frame_number=i,
                file_path=frame_path,
                phash_value=phash,
                pdq_hash=pdq,
                asset_id=asset.id,
            ))
            extracted_count += 1

        # --- Audio fingerprint for the whole file ---
        audio_fp = get_audio_fp(video_path)

        asset.status       = "COMPLETED"
        asset.total_frames = extracted_count
        if audio_fp:
            asset.audio_fp = audio_fp

        db.commit()
        logger.info(
            f"Asset {asset_id} fingerprinted: {extracted_count} frames, "
            f"audio={'yes' if audio_fp else 'no'}"
        )

    except Exception as e:
        db.rollback()
        asset.status = "FAILED"
        db.commit()
        logger.error(f"extract_frames failed for asset {asset_id}: {e}", exc_info=True)

    finally:
        cap.release()
