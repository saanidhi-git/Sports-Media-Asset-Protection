
import os
import sys
import subprocess
import tempfile
import json
import logging

# ── AUTO-INSTALL DEPENDENCIES ──────────────────────────────────────────
def ensure_dependencies():
    deps = ["yt-dlp", "opencv-python", "requests"]
    missing = []
    
    # Check yt-dlp
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")
        
    # Check requests
    try:
        import requests
    except ImportError:
        missing.append("requests")
        
    # Check opencv
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")

    if missing:
        print(f"📦 Setup: Missing {', '.join(missing)}. Installing now...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("✅ Setup complete.")
            return True
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    return True

# ── CONFIGURATION ──────────────────────────────────────────────────────────
# IMPORTANT: The server automatically updates these when you download it!
API_BASE_URL = "https://your-app-on-render.com/api/v1" 
EXTERNAL_AGENT_KEY = "dev-key-123"

# Bundled data (filled during download)
JOB_ID = 0
TARGET_VIDEOS = []
# ───────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("LocalAgent")

def download_and_extract(video_info, tmp_dir):
    import cv2
    url = video_info["url"]
    vid = video_info["platform_video_id"]
    platform = video_info.get("platform", "youtube")
    
    video_path = os.path.join(tmp_dir, f"video_{vid}.mp4")
    audio_path = os.path.join(tmp_dir, f"audio_{vid}.m4a")
    
    # 1. Download (Optimized for Platform)
    logger.info(f"📥 Downloading ({platform}): {url}")
    
    ytdlp_cmd = [
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
        "--download-sections", "*0-60",
        "-o", video_path, url
    ]
    
    # Reddit often needs specific handling for audio/video merge
    if platform == "reddit":
        ytdlp_cmd = ["yt-dlp", "--no-warnings", "--quiet", "-f", "bestvideo+bestaudio/best", "-o", video_path, url]

    subprocess.run(ytdlp_cmd)
    
    # 2. Audio extraction
    subprocess.run([
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestaudio", "--extract-audio", "--audio-format", "m4a",
        "--download-sections", "*0-30",
        "-o", audio_path, url
    ])

    # 3. Frames
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
        sys.exit(1)

    import requests
    videos = TARGET_VIDEOS
    if not videos:
        logger.error(f"No URLs bundled. Please download the script from the dashboard for Job #{job_id}.")
        return

    print("\n" + "="*50)
    print(f"🚀 HYBRID EXTRACTION STARTED — Job #{job_id}")
    print(f"📦 Total targets to process: {len(videos)}")
    print("="*50 + "\n")

    for i, v in enumerate(videos):
        print(f"[{i+1}/{len(videos)}] Processing: {v['title'][:50]}...")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                frames, audio = download_and_extract(v, tmp)
                
                # Push
                files = [("frames", (os.path.basename(f), open(f, "rb"), "image/jpeg")) for f in frames]
                if os.path.exists(audio):
                    files.append(("audio", (os.path.basename(audio), open(audio, "rb"), "audio/mp4")))

                data = {"job_id": job_id, "api_key": EXTERNAL_AGENT_KEY, "metadata_json": json.dumps(v)}
                resp = requests.post(f"{API_BASE_URL}/pipeline/external-push-raw", data=data, files=files)
                
                if resp.status_code == 202:
                    print(f"   ✅ Data pushed successfully.")
                else:
                    print(f"   ❌ Push failed: {resp.text}")
            except Exception as e:
                print(f"   ❌ Error: {e}")

    print("\n" + "="*50)
    print("🏁 ALL TARGETS PROCESSED!")
    print("👉 ACTION: Go back to the dashboard and click 'COMPUTE HASHES & VERIFY'")
    print("="*50 + "\n")

if __name__ == "__main__":
    jid = JOB_ID
    if len(sys.argv) > 1:
        jid = int(sys.argv[1])
    
    if jid == 0:
        print("Usage: python local_agent.py <job_id>")
        sys.exit(1)
        
    process_job(jid)
