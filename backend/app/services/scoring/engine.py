import imagehash
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# New Weights (sum to 1.0)
W_PHASH = 0.30
W_PDQ = 0.25
W_AUDIO = 0.32
W_META = 0.13

# Thresholds
THRESHOLD_FLAG = 0.85
THRESHOLD_REVIEW = 0.60

def phash_similarity(suspect_hashes: List[str], ref_hashes: List[str]) -> float:
    if not suspect_hashes or not ref_hashes:
        return 0.0
        
    scores = []
    for s_hash in suspect_hashes:
        if not s_hash:
            continue
        best_sim = 0.0
        try:
            s_obj = imagehash.hex_to_hash(s_hash)
            for r_hash in ref_hashes:
                if not r_hash:
                    continue
                r_obj = imagehash.hex_to_hash(r_hash)
                dist = s_obj - r_obj
                sim = max(0.0, 1.0 - (dist / 64.0))
                if sim > best_sim:
                    best_sim = sim
            scores.append(best_sim)
        except Exception as e:
            logger.warning(f"Error calculating pHash similarity: {e}")
            
    if not scores:
        return 0.0
        
    return sum(scores) / len(scores)

def pdq_similarity(suspect_hashes: List[str], ref_hashes: List[str]) -> float:
    if not suspect_hashes or not ref_hashes:
        return 0.0
    
    scores = []
    for s_hash in suspect_hashes:
        if not s_hash:
            continue
        best_sim = 0.0
        try:
            v_s = int(s_hash, 16)
            for r_hash in ref_hashes:
                if not r_hash:
                    continue
                v_r = int(r_hash, 16)
                # Hamming distance via XOR and bit count
                dist = bin(v_s ^ v_r).count('1')
                sim = max(0.0, 1.0 - (dist / 64.0))
                if sim > best_sim:
                    best_sim = sim
            scores.append(best_sim)
        except Exception as e:
            logger.warning(f"Error calculating PDQ similarity: {e}")
            
    if not scores:
        return 0.0
        
    return sum(scores) / len(scores)

def audio_similarity(suspect_fp: Optional[str], ref_fp: Optional[str]) -> float:
    if not suspect_fp or not ref_fp:
        return 0.0
    try:
        a = [int(x) for x in suspect_fp.split(",")]
        b = [int(x) for x in ref_fp.split(",")]
        length = min(len(a), len(b), 100)
        
        match = sum(32 - bin((x ^ y) & 0xFFFFFFFF).count("1") for x, y in zip(a[:length], b[:length]))
        score = match / (length * 32)
        return score
    except Exception as e:
        logger.warning(f"Error calculating audio similarity: {e}")
        return 0.0

def metadata_similarity(scraped_text: str, asset_description: str) -> float:
    """
    Returns 0.0–1.0 similarity.
    Updated: Less strict than TF-IDF. Uses token overlap ratio.
    """
    if not scraped_text or not asset_description:
        return 0.0

    try:
        # Preprocessing: lower case and remove common short words
        s_tokens = set(t for t in scraped_text.lower().split() if len(t) > 3)
        a_tokens = set(t for t in asset_description.lower().split() if len(t) > 3)
        
        if not s_tokens or not a_tokens:
            # Fallback to shorter words if no long ones exist
            s_tokens = set(scraped_text.lower().split())
            a_tokens = set(asset_description.lower().split())
            if not s_tokens or not a_tokens:
                return 0.0
            
        intersection = s_tokens.intersection(a_tokens)
        # Lenient: overlap relative to the smaller set of tokens
        score = len(intersection) / min(len(s_tokens), len(a_tokens))
        
        return float(round(min(1.0, score), 4))
    except Exception as e:
        logger.warning(f"Error calculating metadata similarity: {e}")
        return 0.0

def compute_verdict(
    phash_score: float, 
    pdq_score: float, 
    audio_score: float, 
    metadata_score: float = 0.0,
    ai_match: bool = False
) -> Dict:
    has_audio = audio_score > 0
    has_meta = metadata_score > 0
    
    # Calculate weighted total dynamically based on available signals
    active_w = W_PHASH + W_PDQ
    weighted_sum = (W_PHASH * phash_score) + (W_PDQ * pdq_score)
    
    if has_audio:
        active_w += W_AUDIO
        weighted_sum += (W_AUDIO * audio_score)
    
    if has_meta:
        active_w += W_META
        weighted_sum += (W_META * metadata_score)
        
    final_score = weighted_sum / active_w
        
    if final_score >= THRESHOLD_FLAG:
        verdict = "FLAG"
    elif final_score >= THRESHOLD_REVIEW:
        verdict = "REVIEW"
    else:
        verdict = "DROP"

    # --- USER SPECIFIC LOGIC ---
    # 1. AI-Confirmed Match: If AI confirms + all available signals >= 40% -> Force REVIEW
    if ai_match:
        signals_above_40 = (
            phash_score >= 0.4 and 
            pdq_score >= 0.4 and 
            (not has_audio or audio_score >= 0.4) and 
            (not has_meta or metadata_score >= 0.4)
        )
        if signals_above_40:
            logger.info("🤖 AI Confirmed + All signals > 40% -> Forcing REVIEW")
            verdict = "REVIEW"

    # 2. Absolute Match (90%+): If ALL signals >= 0.9 -> Force VIOLATED
    signals_above_90 = (
        phash_score >= 0.9 and 
        pdq_score >= 0.9 and 
        (not has_audio or audio_score >= 0.9) and 
        (not has_meta or metadata_score >= 0.9)
    )
    if signals_above_90:
        logger.info("🚨 Absolute Match -> Forcing VIOLATED status")
        verdict = "VIOLATED"
        
    return {
        "phash_score": float(round(phash_score, 4)),
        "pdq_score": float(round(pdq_score, 4)),
        "audio_score": float(round(audio_score, 4)),
        "metadata_score": float(round(metadata_score, 4)),
        "final_score": float(round(final_score, 4)),
        "verdict": verdict
    }
