"""YouTube scraper — uses the YouTube Data API v3 + yt-dlp."""
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


def scrape_and_fingerprint(query: str, limit: int, num_frames: int = 8, early_exit_score_fn=None) -> list[dict]:
    """
    Search YouTube, fingerprint it, and return a list of result dicts.
    If STREAM_MODE is true, uses hybrid chunk-download (reliable).
    Otherwise downloads the full video.
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

        base_dir = Path("uploads/scraped/youtube") / vid
        base_dir.mkdir(parents=True, exist_ok=True)
        
        frames_dir = str(base_dir / "frames")

        if settings.STREAM_MODE:
            # ── Hybrid chunk-download: single yt-dlp call for video+audio ──
            logger.info(f"   📥 [1/2] Streaming {vid} …")
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
            video_path = str(base_dir / f"{vid}.mp4")
            logger.info(f"   ⬇ [1/4] Downloading YouTube: {vid}...")
            if not run_ytdlp(url, video_path):
                logger.error(f"   ❌ YouTube download failed for {vid}")
                continue

            logger.info(f"   🎞 [2/4] Extracting {num_frames} frames & fingerprinting...")
            fp = fingerprint_video_file(video_path, num_frames=num_frames, save_frames_dir=frames_dir)
            
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
        logger.info(
            f"   ✅ YouTube ✓ {title[:40]} — "
            f"{len(fp.get('phashes', []))} pHashes, "
            f"{len(fp.get('pdq_hashes', []))} PDQ, "
            f"audio={'yes' if fp.get('audio_fp') else 'no'}"
        )

    return results
