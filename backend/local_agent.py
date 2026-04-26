
import os
import sys
import subprocess
import tempfile
import json
import logging
import time
import shutil

# ── AUTO-INSTALL DEPENDENCIES ──────────────────────────────────────────
def ensure_dependencies():
    deps = ["yt-dlp", "requests", "opencv-python", "imagehash", "pillow", "pdqhash"]
    missing = []
    
    modules = ["yt_dlp", "requests", "cv2", "imagehash", "PIL", "pdqhash"]
    for m, d in zip(modules, deps):
        try:
            __import__(m)
        except ImportError:
            missing.append(d)

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

def safe_rmtree(path):
    """Robust delete for Windows permission errors."""
    for i in range(5):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            time.sleep(1)
    # If still failing, ignore it to prevent script crash
    shutil.rmtree(path, ignore_errors=True)

def stream_and_hash(video_info, tmp_dir):
    import cv2
    import imagehash
    from PIL import Image
    import pdqhash
    
    url = video_info["url"]
    vid = video_info["platform_video_id"]
    
    # 1. Get Direct Stream URL
    logger.info(f"🌐 Fetching stream for: {url}")
    try:
        stream_url = subprocess.check_output([
            "yt-dlp", "--no-warnings", "--quiet", "--get-url", 
            "-f", "bestvideo[height<=480]/best[height<=480]/best", 
            url
        ], text=True).strip()
    except Exception as e:
        logger.error(f"Could not get stream URL: {e}")
        return None

    # 2. Extract Audio Segment (Small download, not the whole video)
    audio_path = os.path.join(tmp_dir, f"audio_{vid}.m4a")
    logger.info("🎵 Extracting audio segment (30s)...")
    subprocess.run([
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestaudio", "--extract-audio", "--audio-format", "m4a",
        "--download-sections", "*0-30",
        "-o", audio_path, url
    ], check=True)

    # 3. Capture Frames from Stream (No download)
    logger.info("🎞️  Capturing frames directly from stream...")
    cap = cv2.VideoCapture(stream_url)
    
    phashes = []
    pdq_hashes = []
    frame_files = []
    
    count = 0
    while len(frame_files) < 8 and count < 2000:
        ret, frame = cap.read()
        if not ret: break
        
        # Grab every 120th frame (~every 4 seconds)
        if count % 120 == 0:
            f_path = os.path.join(tmp_dir, f"frame_{vid}_{len(frame_files)}.jpg")
            cv2.imwrite(f_path, frame)
            frame_files.append(f_path)
            
            # Local Hashing (Cloud-Only Hashing was requested, but we keep these as optional metadata)
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            phashes.append(str(imagehash.phash(pil_img)))
            
            pdq_h, _ = pdqhash.compute(cv2.resize(frame, (512, 512)))
            pdq_hashes.append("".join(map(str, pdq_h.flatten().tolist())))
        
        count += 1
    
    cap.release()

    return {
        "phashes": phashes,
        "pdq_hashes": pdq_hashes,
        "frame_files": frame_files
    }

def process_job(job_id):
    if not ensure_dependencies():
        sys.exit(1)

    import requests
    if not TARGET_VIDEOS:
        logger.error("No URLs bundled.")
        return

    print("\n" + "="*50)
    print(f"🚀 HYBRID STREAMING EXTRACTION — Job #{job_id}")
    print("="*50 + "\n")

    for i, v in enumerate(TARGET_VIDEOS):
        print(f"[{i+1}/{len(TARGET_VIDEOS)}] Streaming: {v['title'][:50]}...")
        
        # Manual temp dir for robust Windows cleanup
        tmp = tempfile.mkdtemp(prefix="sports_guardian_")
        try:
            res = stream_and_hash(v, tmp)
            if not res: continue
            
            logger.info("📤 Pushing raw frames to cloud...")
            
            # Open files explicitly in a list, and ensure they close
            opened_files = []
            try:
                files = []
                for f in res["frame_files"]:
                    fh = open(f, "rb")
                    opened_files.append(fh)
                    files.append(("frames", (os.path.basename(f), fh, "image/jpeg")))

                meta = {**v, "phashes": res["phashes"], "pdq_hashes": res["pdq_hashes"]}
                data = {"job_id": job_id, "api_key": EXTERNAL_AGENT_KEY, "metadata_json": json.dumps(meta)}

                resp = requests.post(f"{API_BASE_URL}/pipeline/external-push-raw", data=data, files=files)
                if resp.status_code == 202:
                    print(f"   ✅ SUCCESS: Data pushed.")
                else:
                    print(f"   ❌ FAILED: {resp.text}")
            finally:
                # CRITICAL: Close all file handles before trying to delete the folder
                for fh in opened_files:
                    fh.close()

        except Exception as e:
            print(f"   ❌ Error: {e}")
        finally:
            # Robust delete with retries
            time.sleep(0.5) 
            safe_rmtree(tmp)

    print("\n" + "="*50)
    print("🏁 ALL STREAMS PROCESSED!")
    print("👉 ACTION: Return to dashboard and click 'COMPUTE HASHES & VERIFY'")
    print("="*50 + "\n")

if __name__ == "__main__":
    jid = JOB_ID
    if len(sys.argv) > 1: jid = int(sys.argv[1])
    if jid > 0: process_job(jid)
