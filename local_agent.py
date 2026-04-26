
import os
import sys
import requests
import logging

# Add backend to path so we can import scrapers
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock early_exit_score_fn since we don't want a DB connection locally for a simple agent
def mock_score_fn(phashes, pdq_hashes):
    return 0.0

# ── CONFIGURATION ──────────────────────────────────────────────────────────
# Change these to match your deployment
API_BASE_URL = "https://your-app-on-render.com/api/v1" 
EXTERNAL_AGENT_KEY = "dev-key-123" # Must match EXTERNAL_AGENT_KEY in Render env
# ───────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("LocalAgent")

def run_local_scan(job_id: int, query: str, youtube_limit: int = 3, instagram_limit: int = 2):
    from app.services.scraper import youtube as yt_scraper
    from app.services.scraper import instagram as ig_scraper

    all_items = []

    # 1. Scrape YouTube
    if youtube_limit > 0:
        logger.info(f"🔴 Local Scraping YouTube (limit={youtube_limit})...")
        try:
            yt_items = yt_scraper.scrape_and_fingerprint(query, limit=youtube_limit, early_exit_score_fn=mock_score_fn)
            all_items.extend(yt_items)
        except Exception as e:
            logger.error(f"YouTube failed: {e}")

    # 2. Scrape Instagram
    if instagram_limit > 0:
        logger.info(f"📷 Local Scraping Instagram (limit={instagram_limit})...")
        try:
            ig_items = ig_scraper.scrape_and_fingerprint(query, limit=instagram_limit, early_exit_score_fn=mock_score_fn)
            all_items.extend(ig_items)
        except Exception as e:
            logger.error(f"Instagram failed: {e}")

    if not all_items:
        logger.warning("No items scraped. Check your local environment/internet.")
        return

    # 3. Push to Cloud
    logger.info(f"🚀 Pushing {len(all_items)} results to Cloud API: {API_BASE_URL}")
    payload = {
        "job_id": job_id,
        "api_key": EXTERNAL_AGENT_KEY,
        "items": all_items
    }

    try:
        resp = requests.post(f"{API_BASE_URL}/pipeline/external-push", json=payload)
        if resp.status_code == 202:
            logger.info("✅ Successfully pushed to cloud. Check your Render logs/dashboard.")
        else:
            logger.error(f"❌ Push failed ({resp.status_code}): {resp.text}")
    except Exception as e:
        logger.error(f"Failed to connect to Render: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python local_agent.py <job_id> <query>")
        sys.exit(1)

    jid = int(sys.argv[1])
    q   = " ".join(sys.argv[2:])
    run_local_scan(jid, q)
