import pytest
from app.services.scoring.engine import (
    phash_similarity, 
    pdq_similarity, 
    audio_similarity, 
    metadata_similarity, 
    compute_verdict
)

def test_phash_similarity():
    # Perfect match
    h1 = "ffffffffffffffff"
    assert phash_similarity([h1], [h1]) == 1.0
    
    # Completely different (max dist 64)
    h2 = "0000000000000000"
    # Hex fff... vs 000... should have 64 bit difference
    assert phash_similarity([h1], [h2]) == 0.0
    
    # Empty
    assert phash_similarity([], []) == 0.0

def test_pdq_similarity():
    # Perfect match
    h1 = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    assert pdq_similarity([h1], [h1]) == 1.0
    
    # Empty
    assert pdq_similarity([], []) == 0.0

def test_audio_similarity():
    # Mock fingerprints
    fp1 = "1,2,3"
    fp2 = "1,2,3"
    assert audio_similarity(fp1, fp2) == 1.0
    
    assert audio_similarity(None, None) == 0.0

def test_metadata_similarity():
    text1 = "Lakers vs Celtics full game highlights"
    text2 = "Lakers Celtics highlights 2024"
    score = metadata_similarity(text1, text2)
    assert score > 0.5
    
    assert metadata_similarity("", "") == 0.0

def test_compute_verdict():
    # Case: VIOLATED (All >= 0.9)
    res = compute_verdict(0.95, 0.95, 0.95, 0.95)
    assert res["verdict"] == "VIOLATED"
    
    # Case: FLAG (High score)
    res = compute_verdict(0.88, 0.88, 0.88)
    assert res["verdict"] == "FLAG"
    
    # Case: DROP (Low score)
    res = compute_verdict(0.1, 0.1, 0.1)
    assert res["verdict"] == "DROP"
    
    # Case: AI Forcing REVIEW
    res = compute_verdict(0.45, 0.45, 0.45, ai_match=True)
    assert res["verdict"] == "REVIEW"
