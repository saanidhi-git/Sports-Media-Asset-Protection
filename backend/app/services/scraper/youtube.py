"""YouTube scraper — uses the YouTube Data API v3 + yt-dlp."""
import logging
import tempfile
from pathlib import Path

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.scraper.base import fingerprint_video_file, run_ytdlp

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _api_search(query: str, max_results: int) -> list[dict]:
    from googleapiclient.discovery import build  # optional dep, late import

    youtube  = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
    response = youtube.search().list(
        q=query, part="snippet", type="video",
        maxResults=max_results, order="relevance",
    ).execute()
    return response.get("items", [])


def scrape_and_fingerprint(query: str, limit: int, num_frames: int = 8) -> list[dict]:
    """
    Search YouTube, download each video into a guaranteed-temp-cleaned directory,
    fingerprint it, and return a list of result dicts.
    """
    try:
        items = _api_search(query, limit)
    except Exception as e:
        logger.error(f"❌ YouTube search failed: {e}")
        return []

    results = []
    for item in items:
        vid   = item["id"]["videoId"]
        title = item["snippet"]["title"]
        url   = f"https://www.youtube.com/watch?v={vid}"

        # Use persistent directory instead of tempfile
        base_dir = Path("uploads/scraped/youtube") / vid
        base_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = str(base_dir / f"{vid}.mp4")
        frames_dir = str(base_dir / "frames")
        
        logger.info(f"   ⬇ [1/4] Downloading YouTube: {vid}...")
        if not run_ytdlp(url, video_path):
            logger.error(f"   ❌ YouTube download failed for {vid}")
            continue

        # Pass save_frames_dir so base.py saves the frames to disk
        logger.info(f"   🎞 [2/4] Extracting {num_frames} frames & fingerprinting...")
        fp = fingerprint_video_file(video_path, num_frames=num_frames, save_frames_dir=frames_dir)
        
        # Cleanup video to save space, but keep frames
        try:
            Path(video_path).unlink(missing_ok=True)
        except Exception:
            pass

        results.append({
            "platform":          "youtube",
            "platform_video_id": vid,
            "title":             title,
            "url":               url,
            **fp,
        })
        logger.info(f"   ✅ YouTube ✓ {title[:40]} — {len(fp['phashes'])} pHashes")

    return results
