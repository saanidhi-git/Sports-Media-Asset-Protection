import logging
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings

logger = logging.getLogger(__name__)

def ai_moderate(title: str) -> tuple[str, str]:
    """
    Classifies a post title using an LLM (Qwen2.5) to filter out discussions.
    Returns (decision, reason)
    """
    try:
        # Note: ChatOllama assumes Ollama is running locally.
        # If it's not available, we fail gracefully to HIGHLIGHT.
        llm = ChatOllama(model="qwen2.5:1.5b", temperature=0)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an anti-piracy detection assistant. "
             "Given a social media post title, classify it as either a HIGHLIGHT (video content) or DISCUSSION (text-only). "
             "Reply in format: DECISION | REASON (one sentence)."),
            ("human", "Title: {title}")
        ])
        
        chain = prompt | llm
        resp = chain.invoke({"title": title}).content.strip()
        
        if "|" in resp:
            decision, reason = resp.split("|", 1)
            return decision.strip().upper(), reason.strip()
            
        return ("HIGHLIGHT" if "HIGHLIGHT" in resp.upper() else "DISCUSSION"), resp
        
    except Exception as e:
        logger.warning(f"AI moderation failed (is Ollama running?): {e}")
        return "HIGHLIGHT", "AI moderation unavailable — defaulting to scan."
