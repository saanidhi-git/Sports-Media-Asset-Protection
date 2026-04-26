
import os
import sys
import subprocess
import requests
import tempfile
import json
import cv2
import logging

# ── AUTO-INSTALL YT-DLP ──────────────────────────────────────────────────
def ensure_dependencies():
    try:
        import yt_dlp
        return True
    except ImportError:
        print("📦 yt-dlp missing. Attempting auto-install...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
            print("✅ yt-dlp installed successfully.")
            return True
        except Exception as e:
            print(f"❌ Auto-install failed: {e}")
            return False

# ── CONFIGURATION ──────────────────────────────────────────────────────────
# IMPORTANT: Update this to your live Render backend URL!
API_BASE_URL = "https://your-app-on-render.com/api/v1" 
EXTERNAL_AGENT_KEY = "dev-key-123"
# ───────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("LocalAgent")

def fetch_videos_to_process(job_id):
    """Asks Render for the list of URLs found during the Discovery phase."""
    url = f"{API_BASE_URL}/pipeline/jobs/{job_id}/videos"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.error(f"Failed to fetch videos ({resp.status_code}): {resp.text}")
            return []
    except Exception as e:
        logger.error(f"Network error fetching videos: {e}")
        return []

def download_and_extract(video_info, tmp_dir):
    """Downloads first 60s and extracts 8 frames + audio for a specific video."""
    url = video_info["url"]
    vid = video_info["platform_video_id"]
    
    video_path = os.path.join(tmp_dir, f"video_{vid}.mp4")
    audio_path = os.path.join(tmp_dir, f"audio_{vid}.m4a")
    
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
                frame_file = os.path.join(tmp_dir, f"frame_{vid}_{i}.jpg")
                cv2.imwrite(frame_file, frame)
                frames_to_send.append(frame_file)
    cap.release()
    return frames_to_send, audio_path

def process_job(job_id):
    if not ensure_dependencies():
        logger.error("Could not verify/install yt-dlp. Please install it manually.")
        return

    videos = fetch_videos_to_process(job_id)
    if not videos:
        logger.warning(f"No videos found for Job #{job_id}. Did Discovery finish?")
        return

    logger.info(f"🚀 Found {len(videos)} videos to process locally.")

    for v in videos:
        logger.info(f"🎬 Processing: {v['title']}")
        with tempfile.TemporaryDirectory() as tmp:
            frames, audio = download_and_extract(v, tmp)
            
            # Push to Render
            logger.info(f"📤 Pushing raw data for '{v['title']}' to Cloud...")
            files = [("frames", (os.path.basename(f), open(f, "rb"), "image/jpeg")) for f in frames]
            if os.path.exists(audio):
                files.append(("audio", (os.path.basename(audio), open(audio, "rb"), "audio/mp4")))

            data = {
                "job_id": job_id,
                "api_key": EXTERNAL_AGENT_KEY,
                "metadata_json": json.dumps(v)
            }

            try:
                resp = requests.post(f"{API_BASE_URL}/pipeline/external-push-raw", data=data, files=files)
                if resp.status_code == 202:
                    logger.info(f"✅ SUCCESS: Pushed data for {v['platform_video_id']}")
                else:
                    logger.error(f"❌ FAILED ({resp.status_code}): {resp.text}")
            except Exception as e:
                logger.error(f"Network error pushing data: {e}")

    logger.info("🏁 Local extraction complete. Please return to the website and click 'COMPUTE HASHES & VERIFY'!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python local_agent.py <job_id>")
        sys.exit(1)
    process_job(int(sys.argv[1]))
