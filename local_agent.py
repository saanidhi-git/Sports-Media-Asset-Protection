
import os
import sys
import subprocess
import requests
import tempfile
import json
import cv2
import logging

# ── CONFIGURATION ──────────────────────────────────────────────────────────
# IMPORTANT: Update this to your live Render backend URL!
API_BASE_URL = "https://your-app-on-render.com/api/v1" 
EXTERNAL_AGENT_KEY = "dev-key-123"
# ───────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("LocalAgent")

def get_video_info(query):
    """Uses yt-dlp to search for one video and get metadata."""
    cmd = [
        "yt-dlp", "--no-warnings", "--quiet", "--print", 
        "%(id)s|||%(title)s|||%(description)s|||%(webpage_url)s|||%(channel)s",
        f"ytsearch1:{query}"
    ]
    try:
        res = subprocess.check_output(cmd, text=True).strip()
        parts = res.split("|||")
        return {
            "platform": "youtube",
            "platform_video_id": parts[0],
            "title": parts[1],
            "description": parts[2],
            "url": parts[3],
            "uploader": parts[4]
        }
    except Exception as e:
        logger.error(f"Failed to find video: {e}")
        return None

def download_and_extract(url, tmp_dir):
    """Downloads first 60s and extracts 8 frames + audio."""
    video_path = os.path.join(tmp_dir, "video.mp4")
    audio_path = os.path.join(tmp_dir, "audio.m4a")
    
    # 1. Download segment
    logger.info(f"📥 Downloading segment from {url}...")
    subprocess.run([
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
        "--download-sections", "*0-60",
        "-o", video_path, url
    ])
    
    # 2. Extract Audio
    logger.info("🎵 Extracting audio...")
    subprocess.run([
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestaudio", "--extract-audio", "--audio-format", "m4a",
        "--download-sections", "*0-30",
        "-o", audio_path, url
    ])

    # 3. Extract Frames
    logger.info("🎞 Extracting frames...")
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_to_send = []
    
    if total_frames > 0:
        step = total_frames // 8
        for i in range(8):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
            ret, frame = cap.read()
            if ret:
                frame_file = os.path.join(tmp_dir, f"frame_{i}.jpg")
                cv2.imwrite(frame_file, frame)
                frames_to_send.append(frame_file)
    cap.release()
    return frames_to_send, audio_path

def run_local_raw_scan(job_id, query):
    info = get_video_info(query)
    if not info: return

    with tempfile.TemporaryDirectory() as tmp:
        frames, audio = download_and_extract(info["url"], tmp)
        
        # 4. Push to Render
        logger.info(f"🚀 Pushing raw data to Cloud: {API_BASE_URL}")
        
        files = [("frames", (os.path.basename(f), open(f, "rb"), "image/jpeg")) for f in frames]
        if os.path.exists(audio):
            files.append(("audio", ("audio.m4a", open(audio, "rb"), "audio/mp4")))

        data = {
            "job_id": job_id,
            "api_key": EXTERNAL_AGENT_KEY,
            "metadata_json": json.dumps(info)
        }

        try:
            resp = requests.post(f"{API_BASE_URL}/pipeline/external-push-raw", data=data, files=files)
            if resp.status_code == 202:
                logger.info("✅ SUCCESS: Cloud received raw frames and is processing!")
            else:
                logger.error(f"❌ FAILED ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Network error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python local_agent.py <job_id> <query>")
        sys.exit(1)
    run_local_raw_scan(int(sys.argv[1]), " ".join(sys.argv[2:]))
