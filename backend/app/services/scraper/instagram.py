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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def get_instagram_metadata(url: str) -> dict:
    """
    Extract metadata (title, description, comments, likes, etc.)
    from an Instagram reel/post using yt-dlp's info extraction.
    No cookies or authentication required.
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "getcomments": True,
        "extractor_args": {
            "instagram": {
                "comments": ["20"],
            }
        },
        # Spoof a real browser to reduce blocks
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        "sleep_interval":       2,   # wait 2s between requests
        "max_sleep_interval":   5,   # up to 5s random jitter
        "ignoreerrors":         True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return {}

        raw_comments = info.get("comments") or []
        top_comments = sorted(
            raw_comments,
            key=lambda c: c.get("like_count", 0),
            reverse=True
        )[:5]

        return {
            "title":         info.get("title", ""),
            "description":   info.get("description", ""),
            "uploader":      info.get("uploader", ""),
            "uploader_id":   info.get("uploader_id", ""),
            "like_count":    info.get("like_count"),
            "view_count":    info.get("view_count"),
            "comment_count": info.get("comment_count"),
            "upload_date":   info.get("upload_date"),   # "YYYYMMDD"
            "top_comments": [
                {
                    "author":     c.get("author"),
                    "text":       c.get("text"),
                    "like_count": c.get("like_count", 0),
                    "timestamp":  c.get("timestamp"),
                }
                for c in top_comments
            ],
        }

    except Exception as e:
        logger.warning(f"⚠️ Metadata extraction failed for {url}: {e}")
        return {}


def scrape_and_fingerprint(query: str, limit: int, num_frames: int = 8, early_exit_score_fn=None) -> list[dict]:
    """
    Discover Instagram reel URLs via Tavily, chunk-download or full-download via yt-dlp,
    fingerprint, and return result dicts.
    """
    try:
        raw_results = _tavily_search(query)
    except Exception as e:
        logger.error(f"❌ Tavily search failed: {e}")
        return []

    reels: list[dict] = []
    seen_urls = set()
    
    for r in raw_results:
        url = r.get("url", "")
        if "/reel/" in url or "/p/" in url:
            clean = url.split("?")[0]
            if clean not in seen_urls:
                seen_urls.add(clean)
                reels.append({
                    "url": clean,
                    "description": r.get("content", "")
                })
        if len(reels) >= limit:
            break

    results = []
    for reel in reels:
        url = reel["url"]
        
        # Enrich with rich metadata
        meta = get_instagram_metadata(url)
        
        description = meta.get("description") or reel["description"]
        title = meta.get("title") or f"Instagram Reel {url.rstrip('/').split('/')[-1]}"
        video_id = url.rstrip("/").split("/")[-1]
        
        if settings.STREAM_MODE:
            # ── Pure Streaming ──
            logger.info(f"   📥 [1/2] Streaming Instagram reel {video_id} …")
            stream_url = get_stream_url(url)
            fp = fingerprint_video_stream(
                url=url,
                stream_url=stream_url,
                num_frames=num_frames,
                early_exit_score_fn=early_exit_score_fn,
            )
            fp["audio_fp"] = get_audio_fp_from_stream(url)

        else:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                video_path = tmp.name

            logger.info(f"   ⬇ [1/4] Downloading Instagram: {video_id}...")
            if not run_ytdlp(url, video_path):
                logger.error(f"   ❌ Instagram download failed for {video_id}")
                if os.path.exists(video_path): os.remove(video_path)
                continue

            logger.info(f"   🎞 [2/4] Extracting {num_frames} frames & fingerprinting...")
            fp = fingerprint_video_file(video_path, num_frames=num_frames)
            
            if os.path.exists(video_path): os.remove(video_path)

        results.append({
            "platform":          "instagram",
            "platform_video_id": video_id,
            "title":             title,
            "description":       description,
            "url":               url,
            "uploader":          meta.get("uploader"),
            "like_count":        meta.get("like_count"),
            "view_count":        meta.get("view_count"),
            "comments":          meta.get("top_comments", []),
            **fp,
        })
        logger.info(
            f"   ✅ Instagram ✓ {video_id} — "
            f"{len(fp.get('phashes', []))} pHashes, "
            f"{len(fp.get('pdq_hashes', []))} PDQ, "
            f"audio={'yes' if fp.get('audio_fp') else 'no'}"
        )

    return results
