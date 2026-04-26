
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.scraper import youtube as yt_scraper
from app.services.scraper import instagram as ig_scraper
from app.services.scraper import reddit as rd_scraper
from app.core.config import settings

def test_youtube(query, limit=2):
    print(f"\n🔴 Testing YouTube Discovery (API v3) for: '{query}'")
    try:
        items = yt_scraper._api_search(query, limit)
        print(f"✅ Found {len(items)} items")
        for i, item in enumerate(items):
            print(f"   [{i+1}] {item['snippet']['title']} (https://www.youtube.com/watch?v={item['id']['videoId']})")
    except Exception as e:
        print(f"❌ YouTube failed: {e}")

def test_instagram(query, limit=2):
    print(f"\n📷 Testing Instagram Discovery (Tavily) for: '{query}'")
    try:
        raw_results = ig_scraper._tavily_search(query)
        # Filter for Reels/Posts
        targets = [r for r in raw_results if "/reel/" in r.get("url", "") or "/p/" in r.get("url", "")]
        print(f"✅ Found {len(targets[:limit])} items")
        for i, item in enumerate(targets[:limit]):
            print(f"   [{i+1}] {item.get('title', 'Reel')} ({item.get('url')})")
    except Exception as e:
        print(f"❌ Instagram failed: {e}")

def test_reddit(query, limit=2):
    print(f"\n🟠 Testing Reddit Discovery (Public JSON) for: '{query}'")
    try:
        data = rd_scraper._search_page(query, None)
        children = data.get("data", {}).get("children", [])
        targets = [c['data'] for c in children if rd_scraper._is_video_post(c['data'])]
        print(f"✅ Found {len(targets[:limit])} items")
        for i, item in enumerate(targets[:limit]):
            print(f"   [{i+1}] {item.get('title')} (https://reddit.com{item.get('permalink')})")
    except Exception as e:
        print(f"❌ Reddit failed: {e}")

if __name__ == "__main__":
    q = "Real Salt Lake vs Inter Miami highlights"
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    
    print("🚀 STARTING DISCOVERY API TEST")
    test_youtube(q)
    test_instagram(q)
    test_reddit(q)
