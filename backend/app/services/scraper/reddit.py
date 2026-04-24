"""Reddit scraper — uses the public Reddit JSON API + yt-dlp."""
import logging
import tempfile
import time
from pathlib import Path

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.scraper.base import (
    fingerprint_video_file, 
    run_ytdlp,
    get_stream_url,
    fingerprint_video_stream,
    get_audio_fp_from_stream,
)

logger  = logging.getLogger(__name__)
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "SportGuardianBot/1.0"})

_VIDEO_DOMAINS = {"v.redd.it", "youtube.com", "youtu.be", "streamable.com", "gfycat.com"}


def _is_video_post(post: dict) -> bool:
    if post.get("is_video"):
        return True
    if post.get("post_hint") in ("hosted:video", "rich:video"):
        return True
    url = post.get("url", "").lower()
    return any(d in url for d in _VIDEO_DOMAINS)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.HTTPError),
    reraise=True,
)
def _search_page(query: str, after: str | None) -> dict:
    params = {"q": query, "sort": "relevance", "limit": 100, "raw_json": 1}
    if after:
        params["after"] = after
    resp = _SESSION.get("https://www.reddit.com/search.json", params=params, timeout=15)
    if resp.status_code == 429:
        delay = int(resp.headers.get("Retry-After", 20))
        logger.warning(f"⚠️ Reddit 429 — sleeping {delay}s")
        time.sleep(delay)
        resp.raise_for_status()
    resp.raise_for_status()
    return resp.json()


def scrape_and_fingerprint(query: str, limit: int, num_frames: int = 8, early_exit_score_fn=None) -> list[dict]:
    """
    Page through Reddit search, collect video posts up to `limit`, chunk-download
    or full-download each, fingerprint, and return result dicts.
    """
    posts: list[dict] = []
    after: str | None = None

    while len(posts) < limit:
        try:
            data = _search_page(query, after)
        except Exception as e:
            logger.error(f"❌ Reddit search error: {e}")
            break

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        for child in children:
            p = child["data"]
            if _is_video_post(p) and not any(v.get("id") == p.get("id") for v in posts):
                posts.append(p)
            if len(posts) >= limit:
                break

        after = data.get("data", {}).get("after")
        if not after:
            break

    results = []
    for post in posts:
        post_id   = post.get("id", "unknown")
        title     = post.get("title", "Reddit Video")
        permalink = f"https://reddit.com{post.get('permalink', '')}"
        post_url  = post.get("url", "")

        base_dir = Path("uploads/scraped/reddit") / post_id
        base_dir.mkdir(parents=True, exist_ok=True)
        
        frames_dir = str(base_dir / "frames")

        if settings.STREAM_MODE:
            # ── Pure Streaming ──
            # Try the post URL first (direct video link), fall back to permalink
            target_url = post_url if post_url else permalink
            logger.info(f"   📥 [1/2] Streaming Reddit video {post_id} …")
            
            stream_url = get_stream_url(target_url)
            if not stream_url and target_url != permalink:
                logger.info(f"   🔄 Retrying get_stream_url with permalink for {post_id} …")
                target_url = permalink
                stream_url = get_stream_url(target_url)

            if stream_url:
                fp = fingerprint_video_stream(
                    url=target_url,
                    stream_url=stream_url,
                    num_frames=num_frames,
                    save_frames_dir=frames_dir,
                    early_exit_score_fn=early_exit_score_fn,
                )
                fp["audio_fp"] = get_audio_fp_from_stream(target_url)
            else:
                logger.warning(f"   ❌ Could not get stream URL for Reddit video {post_id}")
                fp = {"phashes": [], "pdq_hashes": [], "audio_fp": None, "frame_paths": [], "early_exit": False}

        else:
            video_path = str(base_dir / f"{post_id}.mp4")
            logger.info(f"   ⬇ [1/4] Downloading Reddit: {post_id}...")
            
            downloaded = any(
                run_ytdlp(u, video_path)
                for u in [permalink, post_url] if u
            )
            if not downloaded:
                logger.warning(f"   ❌ Reddit: could not download {post_id}")
                continue

            logger.info(f"   🎞 [2/4] Extracting {num_frames} frames & fingerprinting...")
            fp = fingerprint_video_file(video_path, num_frames=num_frames, save_frames_dir=frames_dir)
            
            try:
                Path(video_path).unlink(missing_ok=True)
            except Exception:
                pass

        results.append({
            "platform":          "reddit",
            "platform_video_id": post_id,
            "title":             title,
            "url":               permalink,
            "subreddit":         post.get("subreddit", ""),
            **fp,
        })
        logger.info(
            f"   ✅ Reddit ✓ {title[:40]} — "
            f"{len(fp.get('phashes', []))} pHashes, "
            f"{len(fp.get('pdq_hashes', []))} PDQ, "
            f"audio={'yes' if fp.get('audio_fp') else 'no'}"
        )

    return results
