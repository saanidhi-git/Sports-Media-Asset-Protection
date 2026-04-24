# Enhancement Plan: Gemini AI + Metadata Scoring

## Goals
1. **Speed** — Replace local Ollama/Qwen2.5 (slow cold start) with Gemini Flash via OpenRouter (fast, remote, no local GPU needed)
2. **Smarter AI** — Gemini is a far more capable model for nuanced title/description analysis
3. **New Scoring Signal** — Add a `metadata_score` that compares the scraped video's **title + description** against the registered asset's `match_description` field

---

## Current State vs. Target State

| Component | Current | After |
|---|---|---|
| AI Moderator | `ChatOllama(qwen2.5:1.5b)` — local, slow | `Gemini Flash` via OpenRouter REST — fast, remote |
| Scoring weights | pHash=0.20, PDQ=0.30, Audio=0.50 | pHash=0.15, PDQ=0.25, Audio=0.45, **Meta=0.15** |
| `Asset.match_description` | Exists in DB, **completely unused** | Fed into metadata scoring |
| Scraped video description | **Not captured** | Captured from YouTube API / Reddit / Tavily |

---

## Phase 1 — Config & Credentials
**Files:** `.env`, `config.py`

```env
OPENROUTER_API_KEY=sk-or-v1-...
```
```python
# config.py — add one line
OPENROUTER_API_KEY: str = ""
```

---

## Phase 2 — Rewrite AI Moderator with Gemini Flash
**File:** `app/services/decision/ai_moderator.py`

### Drop
- `langchain_ollama`, `langchain_core` — remove entirely
- Local Ollama dependency

### Add
- Raw `httpx.post()` call to `https://openrouter.ai/api/v1/chat/completions`
- Model: `google/gemini-flash-1.5` (sub-1s, cheapest Gemini tier)

### Signature change
```python
# BEFORE
def ai_moderate(title: str) -> tuple[str, str]

# AFTER — description is optional, backwards-compatible
def ai_moderate(title: str, description: str = "") -> tuple[str, str]
```

### Smarter prompt (title + description now)
```
System: You are an anti-piracy detection assistant for a sports media rights platform.
Given a video's title and description, classify it as:
  HIGHLIGHT — actual footage (goals, race clips, match highlights, game replay)
  DISCUSSION — text post, reaction, opinion, podcast, preview, analysis, meme

Reply ONLY as: DECISION | REASON (one sentence, max 20 words).
```

> [!TIP]
> Gemini Flash returns in ~400ms vs. Qwen2.5 local which can take 5–15s cold.
> This alone makes each video process **10–35x faster**.

---

## Phase 3 — Metadata Similarity Score
**File:** `app/services/scoring/engine.py`

### New function: `metadata_similarity()`
Compare the scraped video's title+description against `Asset.match_description`
using **TF-IDF cosine similarity** (no GPU, fast, no new heavy deps):

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def metadata_similarity(scraped_text: str, asset_description: str) -> float:
    """
    Returns 0.0–1.0 cosine similarity between the scraped title+description
    and the registered asset's match_description field.
    """
    if not scraped_text or not asset_description:
        return 0.0

    vec = TfidfVectorizer(stop_words="english")
    tfidf = vec.fit_transform([scraped_text, asset_description])
    score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
    return float(round(score, 4))
```

### Updated weights in `compute_verdict()`
```python
# Old weights (sum to 1.0)
W_PHASH = 0.20
W_PDQ   = 0.30
W_AUDIO = 0.50

# New weights (sum to 1.0)
W_PHASH = 0.15
W_PDQ   = 0.25
W_AUDIO = 0.45
W_META  = 0.15   # ← NEW: metadata description match
```

> [!NOTE]
> Like audio, metadata weight only activates if both `scraped_text` and
> `asset_description` are non-empty — preventing it from penalising assets
> that don't have a `match_description` filled in.

### Updated `compute_verdict()` signature
```python
# BEFORE
def compute_verdict(phash_score, pdq_score, audio_score) -> dict

# AFTER
def compute_verdict(phash_score, pdq_score, audio_score, metadata_score=0.0) -> dict
```
The returned dict gains one new key: `"metadata_score"`.

---

## Phase 4 — Capture Descriptions in Scrapers

### DB Model change: `scraped_videos` table
Add one column to `ScrapedVideo`:
```python
description = Column(Text, nullable=True)
```

**Alembic migration** (auto-generated):
```bash
alembic revision --autogenerate -m "add description to scraped_videos"
alembic upgrade head
```

### Scraper changes (title is already captured, just add description):

| Scraper | Source of description |
|---|---|
| `youtube.py` | `item["snippet"]["description"]` — already in the API response |
| `reddit.py` | `post["selftext"]` — already in the JSON response |
| `instagram.py` | Tavily `result["content"]` snippet — already in response |

No extra API calls needed — all three scrapers already receive the description, just not storing it.

---

## Phase 5 — Wire into Orchestrator
**File:** `app/services/pipeline/orchestrator.py`

### `_match_against_assets()` — two additions

**1. Accept `scraped_text`:**
```python
def _match_against_assets(
    db, scraped_video, suspect_phashes, suspect_pdq_hashes,
    suspect_audio_fp,
    scraped_text: str = "",       # ← NEW (title + description)
    ai_decision=None, ai_reason=None
)
```

**2. Compute `metadata_score` per asset:**
```python
from app.services.scoring.engine import metadata_similarity

m = metadata_similarity(scraped_text, asset.match_description or "")
score_data = compute_verdict(p, pdq, a, metadata_score=m)
```

### `run_pipeline_job()` — pass description through
```python
# Build scraped_text for metadata matching
scraped_text = f"{item['title']} {item.get('description', '')}".strip()

_match_against_assets(
    db, scraped, phashes, pdq_hashes,
    item.get("audio_fp"),
    scraped_text=scraped_text,     # ← NEW
    ai_decision=ai_decision,
    ai_reason=ai_reason,
)
```

Also pass `description` to `ai_moderate()`:
```python
ai_decision, ai_reason = ai_moderate(
    item["title"],
    item.get("description", "")    # ← NEW
)
```

---

## Phase 6 — Schema + API + Frontend

### Schema (`app/schemas/pipeline.py`)
Add `metadata_score` to both `DetectionResultOut` and `EnrichedDetectionResult`:
```python
metadata_score: float = 0.0
```

### DB Model (`detection_results` table)
Add column:
```python
metadata_score = Column(Float, nullable=False, default=0.0)
```
Run Alembic migration.

### Frontend (`scan-job-new.html`)
Add a new score bar for Metadata (alongside pHash, PDQ, Audio):
```html
<div class="score-row">
  <span class="score-label">Metadata (w=0.15)</span>
  <div class="score-bar-track">
    <div class="score-bar-fill meta" [style.width.%]="r.metadata_score * 100"></div>
  </div>
  <span class="score-val">{{ r.metadata_score.toFixed(3) }}</span>
</div>
```

---

## Files to Change

```
MODIFY  backend/.env                                      — add OPENROUTER_API_KEY
MODIFY  backend/app/core/config.py                        — add OPENROUTER_API_KEY field
MODIFY  backend/app/services/decision/ai_moderator.py     — replace Ollama with Gemini
MODIFY  backend/app/services/scoring/engine.py            — add metadata_similarity(), new weights
MODIFY  backend/app/db/models/scraped_video.py            — add description column
MODIFY  backend/app/db/models/detection_result.py         — add metadata_score column
CREATE  backend/alembic/versions/xxx_add_metadata.py      — migration (autogenerated)
MODIFY  backend/app/services/scraper/youtube.py           — capture description
MODIFY  backend/app/services/scraper/instagram.py         — capture description
MODIFY  backend/app/services/scraper/reddit.py            — capture description
MODIFY  backend/app/services/pipeline/orchestrator.py     — wire everything together
MODIFY  backend/app/schemas/pipeline.py                   — add metadata_score to schemas
MODIFY  frontend/src/app/scan-job-new/scan-job-new.html   — add metadata score bar
```

---

## Implementation Order

```
1. Phase 1  → Config + .env (1 min)
2. Phase 2  → ai_moderator.py — biggest speed win, immediate effect
3. Phase 3  → engine.py — metadata_similarity() + updated weights
4. Phase 4  → Scraper description capture + DB model + migration
5. Phase 5  → Orchestrator wiring
6. Phase 6  → Schema + frontend score bar
```

> [!IMPORTANT]
> You need a free OpenRouter account + API key from https://openrouter.ai/keys
> `google/gemini-flash-1.5` costs ~$0.000075 per 1K input tokens — practically free for this use case.

> [!WARNING]
> `sklearn` must be added to `pyproject.toml` dependencies (`scikit-learn`).
> Run `uv add scikit-learn` before implementing Phase 3.
