import imagehash
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# Weights
W_PHASH = 0.20
W_PDQ = 0.30
W_AUDIO = 0.50

# Thresholds
THRESHOLD_FLAG = 0.85
THRESHOLD_REVIEW = 0.60

def phash_similarity(suspect_hashes: List[str], ref_hashes: List[str]) -> float:
    if not suspect_hashes or not ref_hashes:
        return 0.0
        
    distances = []
    for s_hash in suspect_hashes:
        if not s_hash:
            continue
        try:
            s_obj = imagehash.hex_to_hash(s_hash)
            for r_hash in ref_hashes:
                if not r_hash:
                    continue
                r_obj = imagehash.hex_to_hash(r_hash)
                distances.append(s_obj - r_obj)
        except Exception as e:
            logger.warning(f"Error calculating pHash similarity: {e}")
            
    if not distances:
        return 0.0
        
    min_d = min(distances)
    score = max(0.0, 1.0 - (min_d / 64.0))
    return score

def pdq_similarity(suspect_hashes: List[str], ref_hashes: List[str]) -> float:
    if not suspect_hashes or not ref_hashes:
        return 0.0
    
    min_dist = 256
    for s_hash in suspect_hashes:
        if not s_hash:
            continue
        try:
            v_s = int(s_hash, 16)
            for r_hash in ref_hashes:
                if not r_hash:
                    continue
                v_r = int(r_hash, 16)
                # Hamming distance via XOR and bit count
                dist = bin(v_s ^ v_r).count('1')
                if dist < min_dist:
                    min_dist = dist
        except Exception as e:
            logger.warning(f"Error calculating PDQ similarity: {e}")
            
    # Using 64 as a threshold for 0.0 score, similar to original script
    score = max(0.0, 1.0 - (min_dist / 64.0))
    return score

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

def compute_verdict(phash_score: float, pdq_score: float, audio_score: float) -> Dict:
    has_audio = audio_score > 0
    total_w = W_PHASH + W_PDQ
    
    if has_audio:
        total_w += W_AUDIO
        final_score = (W_PHASH / total_w) * phash_score + (W_PDQ / total_w) * pdq_score + (W_AUDIO / total_w) * audio_score
    else:
        # If no audio matched, rely entirely on visual
        final_score = (W_PHASH / total_w) * phash_score + (W_PDQ / total_w) * pdq_score
        
    if final_score >= THRESHOLD_FLAG:
        verdict = "FLAG"
    elif final_score >= THRESHOLD_REVIEW:
        verdict = "REVIEW"
    else:
        verdict = "DROP"
        
    return {
        "phash_score": float(round(phash_score, 4)),
        "pdq_score": float(round(pdq_score, 4)),
        "audio_score": float(round(audio_score, 4)),
        "final_score": float(round(final_score, 4)),
        "verdict": verdict
    }
