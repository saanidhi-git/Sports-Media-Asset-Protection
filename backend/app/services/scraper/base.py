"""
Shared utilities used by all scraper modules.
Scrapers only import from here — never cross-import each other.
"""
import cv2
import glob as _glob
import gc
import logging
import subprocess
import tempfile
import uuid
from pathlib import Path
import random
from typing import Optional
import os
import shutil
import requests

from app.core.config import settings
from app.services.fingerprint.generator import get_audio_fp, get_pdq, get_phash
from app.services.storage.cloudinary_client import upload_image

logger = logging.getLogger(__name__)

def fingerprint_video_file(video_path: str, num_frames: int = 8) -> dict:
    """
    Opens a video, extracts `num_frames` frames, and uploads to Cloudinary.
    Returns: {phashes, pdq_hashes, audio_fp, frame_paths}
    """
    phashes: list[str]    = []
    pdq_hashes: list[str] = []
    frame_paths: list[str] = []
    
    # Use a temp local dir for extraction before cloud upload
    temp_dir = os.path.join(tempfile.gettempdir(), f"sg_frames_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            return {"phashes": phashes, "pdq_hashes": pdq_hashes, "audio_fp": None, "frame_paths": []}
            
        n = min(num_frames, total)
        step = max(1, total // n) if n > 0 else 1
        frame_indices = [i * step for i in range(n)]

        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            
            ph = get_phash(frame)
            pd = get_pdq(frame)
            if ph: phashes.append(ph)
            if pd: pdq_hashes.append(pd)
                
            # Use an individual temp file for the frame
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_frame:
                local_frame_path = tmp_frame.name
            
            # Use lower quality and smaller size for memory efficiency
            cv2.imwrite(local_frame_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            cloud_url = upload_image(local_frame_path, folder="sports-guardian/scraped_frames")
            frame_paths.append(cloud_url)
            
            # Immediate cleanup
            if os.path.exists(local_frame_path):
                os.remove(local_frame_path)
            del frame
            gc.collect()
                    
    finally:
        cap.release()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    return {
        "phashes":    phashes,
        "pdq_hashes": pdq_hashes,
        "audio_fp":   get_audio_fp(video_path),
        "frame_paths": frame_paths,
    }

def run_ytdlp(url: str, output_path: str, timeout: int = 300, download_sections: Optional[str] = None) -> bool:
    """Downloads a video from `url` to `output_path` via yt-dlp."""
    cookie_path = get_yt_dlp_cookies()
    proxy_url = os.getenv("RESIDENTIAL_PROXY_URL")
    try:
        cmd = [
            "yt-dlp", "--no-warnings", "--quiet",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", output_path, "--no-playlist"
        ]
        if cookie_path:
            cmd.extend(["--cookies", cookie_path])
        if proxy_url:
            cmd.extend(["--proxy", proxy_url])
        cmd.append(url)
        
        subprocess.run(
            cmd, check=True, timeout=timeout, capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        return Path(output_path).exists()
    except Exception as e:
        logger.warning(f"run_ytdlp failed for {url}: {e}")
    finally:
        if cookie_path and os.path.exists(cookie_path):
            os.remove(cookie_path)
    return False

def get_stream_url(url: str, timeout: int = 90) -> str | None:
    """Extracts direct CDN stream URL."""
    cookie_path = get_yt_dlp_cookies()
    proxy_url = os.getenv("RESIDENTIAL_PROXY_URL")
    try:
        cmd = [
            "yt-dlp", "--no-warnings", "--quiet",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "-f", "bestvideo/best",
            "--get-url", "--no-playlist", url,
        ]
        if cookie_path:
            cmd.extend(["--cookies", cookie_path])
        if proxy_url:
            cmd.extend(["--proxy", proxy_url])

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        
        # FAIL FAST: Check if we are blocked
        if "confirm you're not a bot" in result.stderr:
            logger.warning(f"🛑 Cloud blocked for {url}. Please use Hybrid Mode.")
            return None

        stream_url = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        if stream_url.startswith("http"):
            return stream_url
    except Exception as e:
        logger.warning(f"get_stream_url error for {url}: {e}")
    finally:
        if cookie_path and os.path.exists(cookie_path):
            os.remove(cookie_path)
    return None

def _probe_duration(url: str, timeout: int = 90) -> float | None:
    """Return video duration in seconds via yt-dlp."""
    cookie_path = get_yt_dlp_cookies()
    proxy_url = os.getenv("RESIDENTIAL_PROXY_URL")
    try:
        cmd = [
            "yt-dlp", "--no-warnings", "--quiet",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "--print", "duration", "--no-playlist", url,
        ]
        if cookie_path:
            cmd.extend(["--cookies", cookie_path])
        if proxy_url:
            cmd.extend(["--proxy", proxy_url])

        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )

        if "confirm you're not a bot" in res.stderr:
            return None

        raw = res.stdout.strip()
        if raw and raw.replace(".", "", 1).isdigit():
            return float(raw)
    except Exception as e:
        logger.warning(f"_probe_duration failed for {url}: {e}")
    finally:
        if cookie_path and os.path.exists(cookie_path):
            os.remove(cookie_path)
    return None

def fingerprint_video_stream(
    url: str,
    stream_url: str,
    num_frames: int = 8,
    early_exit_score_fn=None,
) -> dict:
    """
    Pure Streaming: Seeks directly to timestamps in the network stream and uploads to Cloudinary.
    """
    phashes:     list[str] = []
    pdq_hashes:  list[str] = []
    frame_paths: list[str] = []
    early_exit   = False

    # Temp local dir for extraction
    temp_dir = os.path.join(tempfile.gettempdir(), f"sg_stream_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)

    duration = _probe_duration(url)
    if not duration or duration <= 0:
        duration = 300.0 # Fallback 5m

    # Spread timestamps evenly across duration
    timestamps_ms = [int(duration * (i / max(1, num_frames - 1)) * 1000) for i in range(num_frames)]
    max_ms = int((duration - 1.0) * 1000)
    timestamps_ms = [min(max_ms, max(0, ts)) for ts in timestamps_ms]

    logger.info(f"   📐 Streaming {num_frames} frames across {duration:.1f}s match...")

    cap = cv2.VideoCapture(stream_url)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, settings.STREAM_OPEN_TIMEOUT_MS)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, settings.STREAM_READ_TIMEOUT_MS)

    try:
        for idx, ts_ms in enumerate(timestamps_ms):
            cap.set(cv2.CAP_PROP_POS_MSEC, ts_ms)
            ret, frame = cap.read()
            if not ret:
                continue

            ph = get_phash(frame)
            pd = get_pdq(frame)
            if ph: phashes.append(ph)
            if pd: pdq_hashes.append(pd)

            # Use an individual temp file for the frame
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_frame:
                local_path = tmp_frame.name
            
            try:
                cv2.imwrite(local_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                cloud_url = upload_image(local_path, folder="sports-guardian/scraped_frames")
                frame_paths.append(cloud_url)
            finally:
                if os.path.exists(local_path):
                    os.remove(local_path)
                
            del frame
            gc.collect()

            if early_exit_score_fn and len(phashes) >= 3:
                rolling_score = early_exit_score_fn(phashes, pdq_hashes)
                if rolling_score >= settings.EARLY_EXIT_THRESHOLD:
                    logger.info(f"🛑 Early-exit triggered at {rolling_score:.3f}")
                    early_exit = True
                    break
    except Exception as e:
        logger.warning(f"fingerprint_video_stream error: {e}")
    finally:
        cap.release()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    return {
        "phashes":     phashes,
        "pdq_hashes":  pdq_hashes,
        "audio_fp":    None,
        "frame_paths": frame_paths,
        "early_exit":  early_exit,
    }

import base64

def get_yt_dlp_cookies() -> str | None:
    """Decodes YOUTUBE_COOKIES_B64 env var into a temp file for yt-dlp."""
    b64_content = os.getenv("YOUTUBE_COOKIES_B64")
    if not b64_content:
        raw_content = os.getenv("YOUTUBE_COOKIES")
        if not raw_content:
            logger.info("🍪 No YOUTUBE_COOKIES_B64 or YOUTUBE_COOKIES found in env.")
            return None
        content_bytes = raw_content.encode("utf-8")
        logger.info(f"🍪 Found raw YOUTUBE_COOKIES ({len(content_bytes)} bytes)")
    else:
        try:
            content_bytes = base64.b64decode(b64_content)
            logger.info(f"🍪 Decoded YOUTUBE_COOKIES_B64 ({len(content_bytes)} bytes)")
        except Exception as e:
            logger.error(f"❌ Failed to decode YOUTUBE_COOKIES_B64: {e}")
            return None

    tmp_path = os.path.join(tempfile.gettempdir(), f"cookies_{uuid.uuid4().hex}.txt")
    with open(tmp_path, "wb") as f:
        f.write(content_bytes)
    return tmp_path

def get_audio_fp_from_stream(url: str, duration_sec: int = settings.AUDIO_SEGMENT_DURATION) -> str | None:
    """Downloads a short audio segment for fingerprinting."""
    if shutil.which("fpcalc") is None:
        return None

    tmp_dir = tempfile.mkdtemp(prefix="sgai_audio_")
    output_template = os.path.join(tmp_dir, "audio.%(ext)s")
    
    cookie_path = get_yt_dlp_cookies()
    proxy_url = os.getenv("RESIDENTIAL_PROXY_URL")
    
    try:
        cmd = [
            "yt-dlp", "--no-warnings", "--quiet",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "-f", "bestaudio", "--extract-audio", "--audio-format", "m4a",
            "--download-sections", f"*0-{duration_sec}",
            "-o", output_template, "--no-playlist", url,
        ]
        if cookie_path:
            cmd.extend(["--cookies", cookie_path])
        if proxy_url:
            cmd.extend(["--proxy", proxy_url])

        result = subprocess.run(
            cmd,
            timeout=120, check=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        candidates = _glob.glob(os.path.join(tmp_dir, "audio.*"))
        if candidates and os.path.getsize(candidates[0]) > 0:
            return get_audio_fp(candidates[0])
    except subprocess.CalledProcessError as e:
        logger.warning(f"get_audio_fp_from_stream failed (code {e.returncode}): {e.stderr.strip()}")
    except Exception as e:
        logger.warning(f"get_audio_fp_from_stream failed: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if cookie_path and os.path.exists(cookie_path):
            os.remove(cookie_path)
    return None

def download_image(url: str, output_path: str) -> bool:
    """Downloads an image from a URL to a local file."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        logger.warning(f"download_image failed for {url}: {e}")
        return False
