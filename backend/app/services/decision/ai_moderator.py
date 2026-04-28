import logging
import httpx
from app.core.config import settings
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    title: str
    description: str
    decision: str
    reason: str
    retry_count: int

def call_gemini_moderator(state: AgentState) -> AgentState:
    """
    Calls Gemini Pro via OpenRouter to classify the content.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/google/gemini-cli", # Site URL for OpenRouter
        "X-Title": "Sports Guardian", # Site title for OpenRouter
    }
    
    system_prompt = (
        "You are an anti-piracy detection assistant for a sports media rights platform. "
        "Given a video's title and description, classify it as: "
        "HIGHLIGHT — actual footage (goals, race clips, match highlights, game replay) "
        "DISCUSSION — text post, reaction, opinion, podcast, preview, analysis, meme. "
        "Reply ONLY as: DECISION | REASON (one sentence, max 20 words)."
    )
    
    user_content = f"Title: {state['title']}\nDescription: {state['description']}"
    
    payload = {
        "model": "google/gemini-pro-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.1
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            if "|" in content:
                decision, reason = content.split("|", 1)
                state["decision"] = decision.strip().upper()
                state["reason"] = reason.strip()
            else:
                # Fallback parsing
                state["decision"] = "HIGHLIGHT" if "HIGHLIGHT" in content.upper() else "DISCUSSION"
                state["reason"] = content
                
    except Exception as e:
        logger.warning(f"Gemini moderation call failed: {e}")
        state["decision"] = "HIGHLIGHT"
        state["reason"] = f"AI moderation unavailable: {e}"
        
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
    Classifies a post title and description using Gemini Pro via LangGraph.
    Returns (decision, reason)
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
    Performs a High-Fidelity Contextual Match using Gemini Thinking.
    Returns (score, detailed_reasoning).
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/saanidhi-git/Sports-Media-Asset-Protection",
        "X-Title": "Sports Guardian AI",
    }
    
    # Format comments for context
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
        f"--- REGISTERED ASSET ---\n"
        f"NAME: {asset_name}\n"
        f"OWNER: {asset_owner}\n"
        f"DESCRIPTION: {asset_desc}\n\n"
        f"--- FOUND CONTENT ---\n"
        f"TITLE: {scraped_title}\n"
        f"DESCRIPTION: {scraped_desc}\n"
        f"TOP COMMENTS:\n{comments_str}"
    )
    
    payload = {
        "model": "google/gemini-pro-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.1
    }
    
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # Extract score and reasoning
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
        logger.warning(f"AI Deep Analysis failed: {e}")
        return 0.0, f"AI Analysis Unavailable: {e}"
