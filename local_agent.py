
import os
import sys
import subprocess
import tempfile
import json
import logging

# ── AUTO-INSTALL DEPENDENCIES ──────────────────────────────────────────
def ensure_dependencies():
    deps = ["yt-dlp", "requests"]
    missing = []
    try:
        import yt_dlp
    except ImportError: missing.append("yt-dlp")
    try:
        import requests
    except ImportError: missing.append("requests")

    if missing:
        print(f"📦 Setup: Installing {', '.join(missing)}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
    return True

# ── CONFIGURATION ──────────────────────────────────────────────────────────
API_BASE_URL = "https://your-app-on-render.com/api/v1" 
EXTERNAL_AGENT_KEY = "dev-key-123"
JOB_ID = 0
TARGET_VIDEOS = []
# ───────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("LocalAgent")

def extract_raw_data(video_info, tmp_dir):
    """Grabs raw frames and audio without any hashing."""
    url = video_info["url"]
    vid = video_info["platform_video_id"]
    
    video_path = os.path.join(tmp_dir, f"video_{vid}.mp4")
    audio_path = os.path.join(tmp_dir, f"audio_{vid}.m4a")
    
    # 1. Download small segment
    logger.info(f"📥 Capturing data for: {url}")
    subprocess.run([
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
        "--download-sections", "*0-60", "-o", video_path, url
    ])
    
    # 2. Extract raw audio (30s)
    subprocess.run([
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestaudio", "--extract-audio", "--audio-format", "m4a",
        "--download-sections", "*0-30", "-o", audio_path, url
    ])

    # 3. Extract 8 raw JPG frames via FFMPEG
    logger.info("🎞️ Extracting raw frames...")
    subprocess.run([
        "ffmpeg", "-loglevel", "quiet", "-i", video_path,
        "-vf", "fps=8/60", "-vframes", "8", 
        os.path.join(tmp_dir, f"frame_{vid}_%d.jpg")
    ])
    
    frames = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.startswith(f"frame_{vid}") and f.endswith(".jpg")]
    return sorted(frames), audio_path

def process_job(job_id):
    ensure_dependencies()
    import requests
    
    if not TARGET_VIDEOS:
        logger.error("No URLs found in script.")
        return

    print(f"\n🚀 STARTING RAW DATA EXTRACTION — Job #{job_id}\n")

    for i, v in enumerate(TARGET_VIDEOS):
        print(f"[{i+1}/{len(TARGET_VIDEOS)}] Extracting: {v['title'][:50]}...")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                frames, audio = extract_raw_data(v, tmp)
                
                # Push RAW FILES to Cloud
                files = [("frames", (os.path.basename(f), open(f, "rb"), "image/jpeg")) for f in frames]
                if os.path.exists(audio):
                    files.append(("audio", (os.path.basename(audio), open(audio, "rb"), "audio/mp4")))

                data = {"job_id": job_id, "api_key": EXTERNAL_AGENT_KEY, "metadata_json": json.dumps(v)}
                resp = requests.post(f"{API_BASE_URL}/pipeline/external-push-raw", data=data, files=files)
                
                if resp.status_code == 202:
                    print(f"   ✅ Raw data sent to Cloud.")
                else:
                    print(f"   ❌ Failed to send: {resp.text}")
            except Exception as e:
                print(f"   ❌ Error: {e}")

    print("\n🏁 DONE! Now go to the website and click 'COMPUTE HASHES & VERIFY'\n")

if __name__ == "__main__":
    jid = JOB_ID
    if len(sys.argv) > 1: jid = int(sys.argv[1])
    if jid > 0: process_job(jid)
