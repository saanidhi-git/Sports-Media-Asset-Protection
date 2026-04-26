
import os
import sys
import subprocess
import tempfile
import json
import logging
import base64

# ── AUTO-INSTALL DEPENDENCIES ──────────────────────────────────────────
def ensure_dependencies():
    # Full list for Edge Hashing
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
            print(f"Please run: pip install {' '.join(missing)}")
            return False
    return True

# ── CONFIGURATION ──────────────────────────────────────────────────────────
# IMPORTANT: The server automatically updates these when you download it!
API_BASE_URL = "https://your-app-on-render.com/api/v1" 
EXTERNAL_AGENT_KEY = "dev-key-123"
JOB_ID = 0
TARGET_VIDEOS = []
# ───────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("LocalAgent")

def get_audio_fingerprint(audio_path):
    """Uses fpcalc (must be installed on system) to generate audio hash."""
    try:
        # Check if fpcalc exists
        subprocess.check_output(["fpcalc", "-version"])
        res = subprocess.check_output(["fpcalc", "-raw", audio_path], text=True)
        # Format is: FINGERPRINT=...
        if "FINGERPRINT=" in res:
            return res.split("FINGERPRINT=")[1].strip()
    except Exception:
        logger.warning("⚠️ fpcalc not found or failed. Audio fingerprint will be skipped.")
    return None

def download_and_hash(video_info, tmp_dir):
    import cv2
    import imagehash
    from PIL import Image
    import pdqhash
    
    url = video_info["url"]
    vid = video_info["platform_video_id"]
    platform = video_info.get("platform", "youtube")
    
    video_path = os.path.join(tmp_dir, f"video_{vid}.mp4")
    audio_path = os.path.join(tmp_dir, f"audio_{vid}.m4a")
    
    # 1. Download
    logger.info(f"📥 Downloading ({platform}): {url}")
    ytdlp_cmd = [
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
        "--download-sections", "*0-60",
        "-o", video_path, url
    ]
    if platform == "reddit":
        ytdlp_cmd = ["yt-dlp", "--no-warnings", "--quiet", "-f", "bestvideo+bestaudio/best", "-o", video_path, url]
    subprocess.run(ytdlp_cmd)
    
    # 2. Audio
    subprocess.run([
        "yt-dlp", "--no-warnings", "--quiet",
        "-f", "bestaudio", "--extract-audio", "--audio-format", "m4a",
        "--download-sections", "*0-30",
        "-o", audio_path, url
    ])

    # 3. Local Hashing (EDGE COMPUTE)
    logger.info("⚙️  Generating pHash, PDQ, and Audio fingerprints locally...")
    
    # Audio
    audio_fp = get_audio_fingerprint(audio_path)
    
    # Visual
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    phashes = []
    pdq_hashes = []
    frame_files = []
    
    if total_frames > 0:
        step = total_frames // 8
        for i in range(8):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
            ret, frame = cap.read()
            if ret:
                # Store for upload
                f_path = os.path.join(tmp_dir, f"frame_{vid}_{i}.jpg")
                cv2.imwrite(f_path, frame)
                frame_files.append(f_path)
                
                # pHash
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                phashes.append(str(imagehash.phash(pil_img)))
                
                # PDQ
                pdq_h, _ = pdqhash.compute_hash(cv2.resize(frame, (512, 512)))
                pdq_hashes.append("".join(map(str, pdq_h.flatten().tolist())))

    cap.release()
    return {
        "phashes": phashes,
        "pdq_hashes": pdq_hashes,
        "audio_fp": audio_fp,
        "frame_files": frame_files,
        "audio_file": audio_path if os.path.exists(audio_path) else None
    }

def process_job(job_id):
    if not ensure_dependencies():
        sys.exit(1)

    import requests
    videos = TARGET_VIDEOS
    if not videos:
        logger.error("No URLs bundled. Please download from dashboard.")
        return

    print("\n" + "="*50)
    print(f"🚀 EDGE HASHING STARTED — Job #{job_id}")
    print("="*50 + "\n")

    for i, v in enumerate(videos):
        print(f"[{i+1}/{len(videos)}] Processing: {v['title'][:50]}...")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                res = download_and_hash(v, tmp)
                
                # Push EVERYTHING (Metadata + Hashes + Files)
                logger.info("📤 Pushing hashes and images to cloud...")
                
                files = [("frames", (os.path.basename(f), open(f, "rb"), "image/jpeg")) for f in res["frame_files"]]
                if res["audio_file"]:
                    files.append(("audio", (os.path.basename(res["audio_file"]), open(res["audio_file"], "rb"), "audio/mp4")))

                # Include hashes in metadata
                meta = {**v, "phashes": res["phashes"], "pdq_hashes": res["pdq_hashes"], "audio_fp": res["audio_fp"]}
                
                data = {
                    "job_id": job_id,
                    "api_key": EXTERNAL_AGENT_KEY,
                    "metadata_json": json.dumps(meta)
                }

                resp = requests.post(f"{API_BASE_URL}/pipeline/external-push-raw", data=data, files=files)
                if resp.status_code == 202:
                    print(f"   ✅ SUCCESS: Edge hashing pushed to cloud.")
                else:
                    print(f"   ❌ FAILED: {resp.text}")
            except Exception as e:
                print(f"   ❌ Error: {e}")

    print("\n" + "="*50)
    print("🏁 EDGE EXTRACTION COMPLETE!")
    print("👉 ACTION: Return to dashboard and click 'COMPUTE HASHES & VERIFY'")
    print("="*50 + "\n")

if __name__ == "__main__":
    jid = JOB_ID
    if len(sys.argv) > 1: jid = int(sys.argv[1])
    if jid == 0: sys.exit(1)
    process_job(jid)
