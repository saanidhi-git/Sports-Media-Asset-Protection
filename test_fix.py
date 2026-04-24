import sys
import os
import logging
import subprocess

# Add the backend directory to sys.path so we can import the app modules
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Monkeypatch logger in base.py to see its output more clearly if needed
import app.services.scraper.base as base
base.logger.setLevel(logging.DEBUG)

from app.services.scraper.base import get_audio_fp_from_stream

# Configure logging to see the output
logging.basicConfig(level=logging.DEBUG)

url = "https://www.youtube.com/watch?v=sNd1-1GjMDY"
print(f"Testing get_audio_fp_from_stream for URL: {url}")

# Ensure the .venv/Scripts folder is in the PATH for this test
venv_scripts = os.path.abspath(os.path.join(os.getcwd(), "backend", ".venv", "Scripts"))
os.environ["PATH"] = venv_scripts + os.pathsep + os.environ.get("PATH", "")

# Verify yt-dlp version and location
try:
    ytdlp_check = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
    print(f"Using yt-dlp version: {ytdlp_check.stdout.strip()}")
except Exception as e:
    print(f"Error checking yt-dlp: {e}")

fp = get_audio_fp_from_stream(url)

if fp:
    print(f"SUCCESS! Fingerprint found (first 50 chars): {fp[:50]}...")
else:
    print("FAILED! No fingerprint returned.")
