"""Instagram scraper — uses Tavily to discover reel URLs, yt-dlp to stream or download."""
import logging
import tempfile
from pathlib import Path

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.scraper.base import (
    fingerprint_video_file, 
    run_ytdlp,
    get_stream_url,
    fingerprint_video_stream,
    get_audio_fp_from_stream,
)

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


def scrape_and_fingerprint(query: str, limit: int, num_frames: int = 8, early_exit_score_fn=None) -> list[dict]:
    """
    Discover Instagram reel URLs via Tavily, chunk-download or full-download via yt-dlp,
    fingerprint, and return result dicts.
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
        
        base_dir = Path("uploads/scraped/instagram") / video_id
        base_dir.mkdir(parents=True, exist_ok=True)
        
        frames_dir = str(base_dir / "frames")

        if settings.STREAM_MODE:
            # ── Pure Streaming ──
            logger.info(f"   📥 [1/2] Streaming Instagram reel {video_id} …")
            stream_url = get_stream_url(url)
            fp = fingerprint_video_stream(
                url=url,
                stream_url=stream_url,
                num_frames=num_frames,
                save_frames_dir=frames_dir,
                early_exit_score_fn=early_exit_score_fn,
            )
            fp["audio_fp"] = get_audio_fp_from_stream(url)

        else:
            video_path = str(base_dir / f"{video_id}.mp4")
            logger.info(f"   ⬇ [1/4] Downloading Instagram: {video_id}...")
            if not run_ytdlp(url, video_path):
                logger.error(f"   ❌ Instagram download failed for {video_id}")
                continue

            logger.info(f"   🎞 [2/4] Extracting {num_frames} frames & fingerprinting...")
            fp = fingerprint_video_file(video_path, num_frames=num_frames, save_frames_dir=frames_dir)
            
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
        logger.info(
            f"   ✅ Instagram ✓ {video_id} — "
            f"{len(fp.get('phashes', []))} pHashes, "
            f"{len(fp.get('pdq_hashes', []))} PDQ, "
            f"audio={'yes' if fp.get('audio_fp') else 'no'}"
        )

    return results
