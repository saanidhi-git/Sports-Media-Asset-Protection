import logging
import httpx
import time
from app.core.config import settings
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

# Model Fallback Chain — Free-Tier Models (confirmed working)
MODEL_PRIORITY = [
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-2-9b-it:free",
]

class AgentState(TypedDict):
    title: str
    description: str
    decision: str
    reason: str
    retry_count: int

def call_gemini_moderator(state: AgentState) -> AgentState:
    """
    Calls Gemini Pro via OpenRouter to classify the content.
    Includes retry logic for 429s and automatic model fallback.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/saanidhi-git/Sports-Media-Asset-Protection",
        "X-Title": "Sports Guardian",
    }
    
    system_prompt = (
        "You are an anti-piracy detection assistant for a sports media rights platform. "
        "Given a video's title and description, classify it as: "
        "HIGHLIGHT — actual footage (goals, race clips, match highlights, game replay) "
        "DISCUSSION — text post, reaction, opinion, podcast, preview, analysis, meme. "
        "Reply ONLY as: DECISION | REASON (one sentence, max 20 words)."
    )
    
    user_content = f"{system_prompt}\n\nTitle: {state['title']}\nDescription: {state['description']}"
    
    for model_name in MODEL_PRIORITY:
        logger.info(f"🤖 Attempting moderation with model: {model_name}")
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": 150
        }
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    
                    if resp.status_code == 429:
                        wait_time = (2 ** attempt) + 1
                        logger.warning(f"⚠️ {model_name} Rate Limit (429). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    
                    resp.raise_for_status()
                    data = resp.json()
                    
                    choice = data["choices"][0]
                    message = choice.get("message", {})
                    content = message.get("content")
                    
                    # Handle models that put response in reasoning or if content is null
                    if not content and "reasoning" in message:
                        content = message["reasoning"]
                    
                    if not content:
                        logger.warning(f"Empty content from {model_name}")
                        continue

                    content = content.strip()
                    
                    if "|" in content:
                        decision, reason = content.split("|", 1)
                        state["decision"] = decision.strip().upper()
                        state["reason"] = reason.strip()
                    else:
                        state["decision"] = "HIGHLIGHT" if "HIGHLIGHT" in content.upper() else "DISCUSSION"
                        state["reason"] = content
                    return state
                        
            except Exception as e:
                logger.warning(f"Moderation attempt {attempt+1} failed with {model_name}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    logger.error(f"❌ {model_name} exhausted. Shifting to fallback if available.")
                    break # Break out of retry loop to try next model
        
    # Final fallback if all models fail
    state["decision"] = "HIGHLIGHT"
    state["reason"] = "AI moderation exhausted all models. Defaulting to safe review state."
    return state

# Build the LangGraph
def create_moderation_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("moderator", call_gemini_moderator)
    workflow.set_entry_point("moderator")
    workflow.add_edge("moderator", END)
    return workflow.compile()

moderation_graph = create_moderation_graph()

def ai_moderate(title: str, description: str = "") -> tuple[str, str]:
    """
    Classifies a post title and description using Gemini via LangGraph with fallback support.
    """
    initial_state: AgentState = {
        "title": title,
        "description": description,
        "decision": "",
        "reason": "",
        "retry_count": 0
    }
    
    try:
        final_state = moderation_graph.invoke(initial_state)
        return final_state["decision"], final_state["reason"]
    except Exception as e:
        logger.error(f"LangGraph moderation failed: {e}")
        return "HIGHLIGHT", f"Moderation pipeline error: {e}"

def ai_deep_analysis(
    scraped_title: str, 
    scraped_desc: str, 
    scraped_comments: list[dict],
    asset_name: str, 
    asset_desc: str,
    asset_owner: str
) -> tuple[float, str]:
    """
    Performs a High-Fidelity Contextual Match with automatic model fallback logic.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/saanidhi-git/Sports-Media-Asset-Protection",
        "X-Title": "Sports Guardian AI",
    }
    
    comments_str = "\n".join([f"- {c['author']}: {c['text']}" for c in scraped_comments[:5]])
    if not comments_str:
        comments_str = "No comments available."

    system_prompt = (
        "You are a Senior Sports Media Rights Analyst. Your task is to perform a High-Fidelity Contextual Match "
        "to determine if the found content is a violation of a registered asset.\n\n"
        "You MUST provide your analysis in the following CHAIN OF REACTION structure:\n"
        "1. REGISTERED ASSET: [Identify the asset and its significance]\n"
        "2. CONTENT COMPARISON: [Compare titles and descriptions. Identify shared details like specific years, events, or players.]\n"
        "3. AUDIENCE SIGNALS: [Analyze the top comments. What is the audience confirming? Are they mentioning specific match events or confirming it is a copy?]\n"
        "4. TAKEN REFERENCE: [Conclude where exactly this content takes reference from the asset definition.]\n"
        "\n"
        "Output Format:\n"
        "SCORE: [0.0 to 1.0]\n"
        "REASONING: [The 4-step Chain of Reaction report described above.]"
    )
    
    user_content = (
        f"{system_prompt}\n\n"
        f"--- REGISTERED ASSET ---\n"
        f"NAME: {asset_name}\n"
        f"OWNER: {asset_owner}\n"
        f"DESCRIPTION: {asset_desc}\n\n"
        f"--- FOUND CONTENT ---\n"
        f"TITLE: {scraped_title}\n"
        f"DESCRIPTION: {scraped_desc}\n"
        f"TOP COMMENTS:\n{comments_str}"
    )
    
    for model_name in MODEL_PRIORITY:
        logger.info(f"🧐 Deep Analysis attempting with: {model_name}")
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=25.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    
                    if resp.status_code == 429:
                        wait_time = (attempt * 5) + 5
                        logger.warning(f"⚠️ {model_name} Rate Limit (429). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                        
                    resp.raise_for_status()
                    data = resp.json()
                    message = data["choices"][0].get("message", {})
                    content = message.get("content")
                    
                    if not content and "reasoning" in message:
                        content = message["reasoning"]
                    
                    if not content:
                        logger.warning(f"Empty content from {model_name} in deep analysis")
                        continue

                    content = content.strip()
                    
                    score = 0.0
                    reasoning = "AI Analysis Error: Response format mismatch."
                    
                    import re
                    score_match = re.search(r"SCORE:\s*([0-1]\.[0-9]+|[01])", content, re.IGNORECASE)
                    if score_match:
                        score = float(score_match.group(1))
                    
                    reason_match = re.search(r"REASONING:\s*(.*)", content, re.IGNORECASE | re.DOTALL)
                    if reason_match:
                        reasoning = reason_match.group(1).strip()
                    
                    return score, reasoning
                    
            except Exception as e:
                logger.warning(f"Deep Analysis attempt {attempt+1} failed with {model_name}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    logger.error(f"❌ {model_name} exhausted for deep analysis. Shifting to fallback.")
                    break
                    
    return 0.0, "AI Analysis Unavailable: All models in priority chain exhausted."
