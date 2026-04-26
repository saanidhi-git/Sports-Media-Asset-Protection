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
from app.services.storage.cloudinary_client import upload_image

logger = logging.getLogger(__name__)


def extract_frames(db: Session, asset_id: int, num_frames: int, video_path: str = None):
    """
    Background task: extracts evenly-spaced frames from a registered asset video,
    computes pHash + PDQ per-frame and audio fingerprint for the whole file,
    uploads frames to Cloudinary, and persists all embeddings to the database.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        logger.error(f"extract_frames: Asset {asset_id} not found.")
        return

    # If video_path is not provided (e.g. for already uploaded assets), we use media_file_path
    # but for new registrations, we pass the local temp path.
    if not video_path:
        video_path = asset.media_file_path

    if not os.path.exists(video_path):
        # If it's a URL, we might need to download it first if we want to process it.
        # But for new uploads, we are passing the local /tmp path.
        logger.error(f"extract_frames: Video not found at {video_path}")
        asset.status = "FAILED"
        db.commit()
        return

    # Use a temp directory for extracted frames
    frames_dir = os.path.join(os.path.dirname(video_path), "frames_tmp")
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
                continue

            # --- Fingerprinting ---
            phash = get_phash(frame)
            pdq   = get_pdq(frame)

            # --- Save temporarily and upload to Cloudinary ---
            frame_filename = f"frame_{i:04d}_{uuid.uuid4().hex[:8]}.jpg"
            temp_frame_path = os.path.join(frames_dir, frame_filename)
            cv2.imwrite(temp_frame_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            
            try:
                cloudinary_url = upload_image(temp_frame_path)
            finally:
                if os.path.exists(temp_frame_path):
                    os.remove(temp_frame_path)

            # Free the raw frame array
            del frame
            gc.collect()

            # --- Persist to DB ---
            db.add(AssetFrame(
                frame_number=i,
                file_path=cloudinary_url,
                phash_value=phash,
                pdq_hash=pdq,
                asset_id=asset.id,
            ))
            extracted_count += 1

        # --- Audio fingerprint ---
        audio_fp = get_audio_fp(video_path)

        asset.status       = "COMPLETED"
        asset.total_frames = extracted_count
        if audio_fp:
            asset.audio_fp = audio_fp

        db.commit()
        logger.info(f"Asset {asset_id} processed. Frames uploaded to Cloudinary.")

    except Exception as e:
        db.rollback()
        asset.status = "FAILED"
        db.commit()
        logger.error(f"extract_frames failed for asset {asset_id}: {e}", exc_info=True)

    finally:
        cap.release()
        # Clean up local video file if it was a temp file
        if "/tmp" in video_path or "temp" in video_path:
            if os.path.exists(video_path):
                os.remove(video_path)
        if os.path.exists(frames_dir):
            shutil.rmtree(frames_dir, ignore_errors=True)
