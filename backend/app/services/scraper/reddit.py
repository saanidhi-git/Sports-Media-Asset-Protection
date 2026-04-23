"""Reddit scraper — uses the public Reddit JSON API + yt-dlp."""
import logging
import tempfile
import time
from pathlib import Path

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.services.scraper.base import fingerprint_video_file, run_ytdlp

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


def scrape_and_fingerprint(query: str, limit: int, num_frames: int = 8) -> list[dict]:
    """
    Page through Reddit search, collect video posts up to `limit`, download
    each into a persistent dir, fingerprint, and return result dicts.
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

        # Use persistent directory
        base_dir = Path("uploads/scraped/reddit") / post_id
        base_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = str(base_dir / f"{post_id}.mp4")
        frames_dir = str(base_dir / "frames")

        logger.info(f"   ⬇ [1/4] Downloading Reddit: {post_id}...")
        downloaded = any(
            run_ytdlp(u, video_path)
            for u in [permalink, post_url] if u
        )
        if not downloaded:
            logger.warning(f"   ❌ Reddit: could not download {post_id}")
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
            "platform":          "reddit",
            "platform_video_id": post_id,
            "title":             title,
            "url":               permalink,
            "subreddit":         post.get("subreddit", ""),
            **fp,
        })
        logger.info(f"   ✅ Reddit ✓ {title[:40]} — {len(fp['phashes'])} pHashes")

    return results
