"""Instagram scraper — uses Tavily to discover reel URLs, yt-dlp to download."""
import logging
import tempfile
from pathlib import Path

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.scraper.base import fingerprint_video_file, run_ytdlp

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _tavily_search(query: str) -> list[dict]:
    from tavily import TavilyClient  # optional dep, late import

    client   = TavilyClient(api_key=settings.TAVILY_API_KEY)
    response = client.search(
        query=f'"{query}" reel video highlights',
        search_depth="advanced",
        include_domains=["instagram.com"],
        max_results=20,
    )
    return response.get("results", [])


def scrape_and_fingerprint(query: str, limit: int, num_frames: int = 8) -> list[dict]:
    """
    Discover Instagram reel URLs via Tavily, download via yt-dlp into a
    persistent dir, fingerprint, and return result dicts.
    """
    try:
        raw = _tavily_search(query)
    except Exception as e:
        logger.error(f"❌ Tavily search failed: {e}")
        return []

    reel_urls: list[str] = []
    for r in raw:
        url = r.get("url", "")
        if "/reel/" in url or "/p/" in url:
            clean = url.split("?")[0]
            if clean not in reel_urls:
                reel_urls.append(clean)
        if len(reel_urls) >= limit:
            break

    results = []
    for url in reel_urls:
        video_id = url.rstrip("/").split("/")[-1]
        
        # Use persistent directory
        base_dir = Path("uploads/scraped/instagram") / video_id
        base_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = str(base_dir / f"{video_id}.mp4")
        frames_dir = str(base_dir / "frames")

        logger.info(f"   ⬇ [1/4] Downloading Instagram: {video_id}...")
        if not run_ytdlp(url, video_path):
            logger.error(f"   ❌ Instagram download failed for {video_id}")
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
            "platform":          "instagram",
            "platform_video_id": video_id,
            "title":             f"Instagram Reel {video_id}",
            "url":               url,
            **fp,
        })
        logger.info(f"   ✅ Instagram ✓ {video_id} — {len(fp['phashes'])} pHashes")

    return results
