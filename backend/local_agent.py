
import os
import sys
import subprocess
import tempfile
import json
import logging
import time

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
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("✅ Dependencies installed.")
            return True
        except Exception as e:
            print(f"❌ Auto-install failed: {e}")
            return False
    return True

# ── CONFIGURATION ──────────────────────────────────────────────────────────
# Server updates this URL during download
API_BASE_URL = "https://your-app-on-render.com/api/v1" 
EXTERNAL_AGENT_KEY = "dev-key-123"
JOB_ID = 0
TARGET_VIDEOS = []
# ───────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("LocalAgent")

def extract_stream_data(video_info, tmp_dir):
    """Uses ffmpeg to capture data directly from the stream (fast)."""
    url = video_info["url"]
    vid = video_info["platform_video_id"]
    
    # 1. Get Direct Stream URL
    logger.info(f"🌐 Fetching stream link: {url}")
    try:
        stream_url = subprocess.check_output([
            "yt-dlp", "--no-warnings", "--quiet", "--get-url", 
            "-f", "bestvideo[height<=480]/best[height<=480]/best", 
            url
        ], text=True).strip()
    except Exception as e:
        logger.error(f"   ❌ Could not get stream: {e}")
        return None, None

    # 2. Extract Audio Segment (Small 30s chunk)
    audio_path = os.path.join(tmp_dir, f"audio_{vid}.m4a")
    logger.info("🎵 Capturing audio chunk...")
    subprocess.run([
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestaudio", "--extract-audio", "--audio-format", "m4a",
        "--download-sections", "*0-30",
        "-o", audio_path, url
    ], capture_output=True)

    # 3. Extract 8 Frames via FFMPEG (Much faster than OpenCV)
    logger.info("🎞️  Capturing 8 frames from stream...")
    subprocess.run([
        "ffmpeg", "-loglevel", "quiet", "-i", stream_url,
        "-vf", "fps=1/5", "-vframes", "8", 
        os.path.join(tmp_dir, f"frame_{vid}_%d.jpg")
    ], capture_output=True)
    
    frames = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.startswith(f"frame_{vid}") and f.endswith(".jpg")]
    return sorted(frames), audio_path

def process_job(job_id):
    # Fix for Windows encoding issues with surrogate characters in video titles
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    if not ensure_dependencies():
        sys.exit(1)

    import requests
    if not TARGET_VIDEOS:
        logger.error("No URLs found. Please start a scan on the website first.")
        return

    print("\n" + "="*50)
    print(f"🚀 FAST HYBRID EXTRACTION — Job #{job_id}")
    print("="*50 + "\n")

    for i, v in enumerate(TARGET_VIDEOS):
        print(f"[{i+1}/{len(TARGET_VIDEOS)}] Streaming: {v['title'][:50]}...")
        tmp = tempfile.mkdtemp(prefix="sports_guardian_")
        try:
            frames, audio = extract_stream_data(v, tmp)
            if not frames: 
                logger.warning(f"   ⚠️ Reporting extraction failure to cloud...")
                try:
                    requests.post(f"{API_BASE_URL}/pipeline/external-push-failed", data={
                        "job_id": job_id, "api_key": EXTERNAL_AGENT_KEY, 
                        "platform_video_id": v["platform_video_id"]
                    })
                except Exception as e:
                    pass
                continue
            
            logger.info("📤 Pushing raw data to cloud...")
            
            opened_files = []
            try:
                files = []
                for f in frames:
                    fh = open(f, "rb")
                    opened_files.append(fh)
                    files.append(("frames", (os.path.basename(f), fh, "image/jpeg")))

                if os.path.exists(audio):
                    af = open(audio, "rb")
                    opened_files.append(af)
                    files.append(("audio", (os.path.basename(audio), af, "audio/mp4")))

                data = {"job_id": job_id, "api_key": EXTERNAL_AGENT_KEY, "metadata_json": json.dumps(v)}
                resp = requests.post(f"{API_BASE_URL}/pipeline/external-push-raw", data=data, files=files)
                
                if resp.status_code == 202:
                    print(f"   ✅ Data pushed successfully.")
                else:
                    print(f"   ❌ Cloud error: {resp.text}")
            finally:
                for fh in opened_files: fh.close()

        except Exception as e:
            print(f"   ❌ Script error: {e}")
        finally:
            time.sleep(0.5)
            try:
                import shutil
                shutil.rmtree(tmp, ignore_errors=True)
            except: pass

    print("\n" + "="*50)
    print("🏁 ALL TARGETS UPLOADED!")
    print("👉 ACTION: Return to dashboard and click 'COMPUTE HASHES & VERIFY'")
    print("="*50 + "\n")

if __name__ == "__main__":
    jid = JOB_ID
    if len(sys.argv) > 1: jid = int(sys.argv[1])
    if jid > 0: process_job(jid)
