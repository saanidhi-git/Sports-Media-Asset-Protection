import sys
import os
from pathlib import Path

# Add backend to path so we can import app
sys.path.append(str(Path(__file__).parent / "backend"))

from backend.app.services.decision.ai_moderator import ai_moderate
from backend.app.core.config import settings

def test_moderation():
    print(f"Testing Gemini Flash Moderation via OpenRouter...")
    print(f"API Key present: {'Yes' if settings.OPENROUTER_API_KEY else 'No'}")
    
    test_cases = [
        {
            "title": "Full Match Replay: Manchester City vs Arsenal 2026",
            "description": "Watch the full highlights and replay of the intense match between City and Arsenal."
        },
        {
            "title": "What do you think about the match last night?",
            "description": "I feel like the referee made some bad calls. Let's discuss in the comments."
        }
    ]
    
    for case in test_cases:
        print(f"\n--- Testing: {case['title']} ---")
        decision, reason = ai_moderate(case['title'], case['description'])
        print(f"DECISION: {decision}")
        print(f"REASON:   {reason}")

if __name__ == "__main__":
    test_moderation()
