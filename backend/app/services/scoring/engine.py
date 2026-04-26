import imagehash
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# Weights from reference script (v6.0)
W_PHASH = 0.25
W_PDQ = 0.35
W_AUDIO = 0.40

# Thresholds
THRESHOLD_VIOLATED = 0.85
THRESHOLD_REVIEW = 0.55

def phash_similarity(suspect_hashes: List[str], ref_hashes: List[str]) -> float:
    if not suspect_hashes or not ref_hashes:
        return 0.0
        
    try:
        distances = []
        for s_hash in suspect_hashes:
            if not s_hash: continue
            s_obj = imagehash.hex_to_hash(s_hash)
            for r_hash in ref_hashes:
                if not r_hash: continue
                r_obj = imagehash.hex_to_hash(r_hash)
                distances.append(s_obj - r_obj)
        
        if not distances:
            return 0.0
            
        min_d = min(distances)
        # Using 64 as threshold for 0.0 score as per reference
        score = max(0.0, 1.0 - (min_d / 64.0))
        return float(round(score, 4))
    except Exception as e:
        logger.warning(f"Error calculating pHash similarity: {e}")
        return 0.0

def pdq_similarity(suspect_hashes: List[str], ref_hashes: List[str]) -> float:
    if not suspect_hashes or not ref_hashes:
        return 0.0
    
    try:
        min_dist = 256
        for s_hash in suspect_hashes:
            if not s_hash: continue
            v_s = int(s_hash, 16)
            for r_hash in ref_hashes:
                if not r_hash: continue
                v_r = int(r_hash, 16)
                # Hamming distance via XOR and bit count
                dist = bin(v_s ^ v_r).count('1')
                if dist < min_dist:
                    min_dist = dist
        
        # PDQ is 256-bit. A distance of 128 is "random". 
        # We use 100 as the 0.0 threshold to be more sensitive to matches.
        score = max(0.0, 1.0 - (min_dist / 100.0))
        return float(round(score, 4))
    except Exception as e:
        logger.warning(f"Error calculating PDQ similarity: {e}")
        return 0.0

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
    if not scraped_text or not asset_description:
        return 0.0

    try:
        s_tokens = set(t for t in scraped_text.lower().split() if len(t) > 3)
        a_tokens = set(t for t in asset_description.lower().split() if len(t) > 3)
        
        if not s_tokens or not a_tokens:
            s_tokens = set(scraped_text.lower().split())
            a_tokens = set(asset_description.lower().split())
            if not s_tokens or not a_tokens:
                return 0.0
            
        intersection = s_tokens.intersection(a_tokens)
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
    total_w = W_PHASH + W_PDQ

    if has_audio:
        total_w += W_AUDIO
        final_score = (W_PHASH / total_w) * phash_score + (W_PDQ / total_w) * pdq_score + (W_AUDIO / total_w) * audio_score
    else:
        final_score = (W_PHASH / total_w) * phash_score + (W_PDQ / total_w) * pdq_score

    # Include Metadata as a booster for the final ranking
    if has_meta:
        final_score = (final_score * 0.8) + (metadata_score * 0.2)

    if final_score >= THRESHOLD_VIOLATED:
        verdict = "VIOLATED"
    elif final_score >= THRESHOLD_REVIEW:
        verdict = "REVIEW"
    else:
        verdict = "CLEAN"

    # AI Override Logic
    if ai_match and verdict == "CLEAN" and final_score > 0.4:
        logger.info("🤖 AI Confirmed Match -> Promoting CLEAN to REVIEW")
        verdict = "REVIEW"

    # Absolute Visual Match (90%+)
    if phash_score >= 0.9 and pdq_score >= 0.8:
        logger.info("🚨 High Visual Match -> Forcing VIOLATED status")
        verdict = "VIOLATED"
        
    return {
        "phash_score": float(round(phash_score, 4)),
        "pdq_score": float(round(pdq_score, 4)),
        "audio_score": float(round(audio_score, 4)),
        "metadata_score": float(round(metadata_score, 4)),
        "final_score": float(round(final_score, 4)),
        "verdict": verdict
    }

