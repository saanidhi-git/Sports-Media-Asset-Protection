"""
Shared utilities used by all scraper modules.
Scrapers only import from here — never cross-import each other.
"""
import cv2
import logging
import subprocess
import tempfile
from pathlib import Path
import random
from typing import Optional

from app.services.fingerprint.generator import get_audio_fp, get_pdq, get_phash

logger = logging.getLogger(__name__)


import os
def fingerprint_video_file(video_path: str, num_frames: int = 8, save_frames_dir: str = None) -> dict:
    """
    Opens a video, extracts `num_frames` frames.
    If num_frames > 40, applies Game Theory optimal sampling (Stratified Random Sampling)
    to minimize computational cost while maximizing the probability of catching short pirate clips.
    Always releases the cv2 cap even on error.
    Returns: {phashes, pdq_hashes, audio_fp}
    """
    phashes: list[str]    = []
    pdq_hashes: list[str] = []
    frame_paths: list[str] = []
    
    if save_frames_dir:
        os.makedirs(save_frames_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            return {"phashes": phashes, "pdq_hashes": pdq_hashes, "audio_fp": None}
            
        n = min(num_frames, total)
        
        # --- MATHEMATICAL OPTIMIZATION (GAME THEORY) ---
        # If a user requests > 40 frames, analyzing all of them is computationally expensive.
        # From a Minimax perspective, the "Pirate" wants to hide a small clip.
        # If we use uniform deterministic sampling, the pirate can predict our intervals.
        # If we use purely random sampling, we might get clusters of frames and leave large gaps.
        # The optimal strategy is "Stratified Random Sampling" capped at a computational bound (e.g., 40).
        # We divide the video into 40 strata and pick a random frame within each stratum.
        # This guarantees maximum coverage distance while maintaining unpredictability.
        if n > 40:
            logger.info(f"Applying Game Theory optimal sampling. Reducing {n} frames to 40 stratified random frames.")
            n = 40
            strata_size = total // n
            frame_indices = [
                random.randint(i * strata_size, min((i + 1) * strata_size - 1, total - 1))
                for i in range(n)
            ]
        else:
            step = max(1, total // n) if n > 0 else 1
            frame_indices = [i * step for i in range(n)]

        for idx in frame_indices:
            if idx >= total:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            ph = get_phash(frame)
            pd = get_pdq(frame)
            if ph:
                phashes.append(ph)
            if pd:
                pdq_hashes.append(pd)
                
            if save_frames_dir:
                # Save frame image
                frame_path = os.path.join(save_frames_dir, f"frame_{idx:05d}.jpg")
                cv2.imwrite(frame_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                frame_paths.append(frame_path)
    except Exception as e:
        logger.warning(f"fingerprint_video_file: {e}")
    finally:
        cap.release()

    return {
        "phashes":    phashes,
        "pdq_hashes": pdq_hashes,
        "audio_fp":   get_audio_fp(video_path),
        "frame_paths": frame_paths,
    }


def run_ytdlp(url: str, output_path: str, timeout: int = 300) -> bool:
    """
    Downloads a video from `url` to `output_path` via yt-dlp.
    Returns True on success, False on any failure.
    """
    try:
        subprocess.run(
            [
                "yt-dlp", "--no-warnings", "--quiet",
                "--extractor-args", "youtube:player_client=android,web_creator",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "-o", output_path, "--no-playlist", url,
            ],
            check=True,
            timeout=timeout,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return Path(output_path).exists()
    except subprocess.CalledProcessError as e:
        logger.warning(f"yt-dlp CalledProcessError for {url}: {e.stderr[:200]}")
    except subprocess.TimeoutExpired:
        logger.warning(f"yt-dlp timeout for {url}")
    except Exception as e:
        logger.warning(f"yt-dlp unexpected error for {url}: {e}")
    return False
