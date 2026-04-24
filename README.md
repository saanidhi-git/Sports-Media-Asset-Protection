# 🛡️ SHIELD_MEDIA: Advanced Sports Media Asset Protection

**SHIELD_MEDIA** is a high-performance, anti-piracy ecosystem designed for sports media rights holders. It provides a "Mission Control" interface to register protected assets, deploy scraping nodes across social platforms, and identify copyright infringements using multi-modal fingerprinting (Visual & Audio).

---

## 🚀 Core Features

### 1. Asset Vault (Digital Fingerprinting)
- **Ingestion:** Upload high-value sports media (clips, match highlights).
- **pHash & PDQ Vectors:** Generates perceptual hashes using `imagehash` and `pdqhash` for visual matching that is resistant to resizing, compression, and slight modifications.
- **Automated Frame Extraction:** Uses `OpenCV` to extract critical frames for high-fidelity comparison.

### 2. Scanning Operations (The Pipeline)
- **Multi-Platform Scraping:** Integrates `yt-dlp`, `Google YouTube Data API`, and `Tavily Discovery` to find suspect videos on YouTube, Instagram, and Reddit.
- **Intelligent Discovery:** Target query-based searches (e.g., "IPL 2026 live stream", "Real Madrid vs Barca goals").
- **Live Terminal Tracking:** Real-time feedback of the scraping and analysis progress via background tasks.

### 3. Verdict Engine (AI Moderation)
- **Scoring System:** Calculates a "Final Threat Score" based on pHash similarity, PDQ geometry matching, and audio fingerprinting.
- **AI Decision Support:** Integrates with `Ollama` for high-level judge reviews and automated decision reasoning.
- **Verdict States:**
  - 🚨 **FLAG:** High-confidence match; immediate violation confirmed.
  - ⚠️ **REVIEW:** Moderate-confidence; requires operator confirmation.
  - ✅ **CLEAN:** No significant match detected.

---

## 🛠️ Technical Stack

### Backend (The Node)
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12)
- **Architecture:** Async-first, RESTful API with background tasks for heavy processing.
- **Persistence:** SQLAlchemy ORM with PostgreSQL.
- **Migrations:** Alembic.
- **Heavy Lift Libraries:**
  - `opencv-python`: Visual processing & frame extraction.
  - `imagehash` & `pdqhash`: Perceptual hashing.
  - `yt-dlp`: Universal video scraping.
  - `google-api-python-client`: Official YouTube integration.

### Frontend (Mission Control)
- **Framework:** [Angular 19+](https://angular.dev/)
- **Paradigm:** Standalone Components & Signals for reactive state management.
- **Aesthetic:** Neo-Brutalism UI design featuring thick borders, sharp 0px corners, hard box shadows, and high-contrast neon accents on a dark canvas.
- **Security:** Functional Auth Guards and Token Interceptors for secure terminal access.

---

## 📂 Project Structure

```text
D:\Projects\Sports-Media-Asset-Protection\
├── backend/
│   ├── app/
│   │   ├── api/v1/        # Endpoints (Assets, Pipeline, Auth, Review)
│   │   ├── db/models/     # SQLAlchemy Models (ScanJob, DetectionResult, etc.)
│   │   ├── services/      # Business Logic (Fingerprint Generator, Scrapers, Orchestrator)
│   │   └── main.py        # Application Entry
│   ├── alembic/           # Database Migration Scripts
│   └── pyproject.toml     # UV Dependency Configuration
└── frontend/
    ├── src/app/
    │   ├── core/          # Services, Guards, Interceptors
    │   ├── home/          # Main Dashboard & Mission Control
    │   ├── register-asset/# Asset Ingestion Logic
    │   ├── scan-job-new/  # Active Scan Terminal
    │   └── scan-jobs-history/ # Audit Logs of all jobs
    └── angular.json       # Project Config
```

---

## ⚙️ Installation & Setup

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **PostgreSQL** (Active instance)
- **Ollama** (Optional, for AI-based moderation)

### 1. Backend Setup
```bash
cd backend
# Install dependencies using UV
uv sync

# Configure Environment
cp .env.example .env # Update DATABASE_URL and API Keys

# Run Migrations
alembic upgrade head

# Start API Server
fastapi dev app/main.py
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm start
```
*Access the terminal at `http://localhost:4200`*

---

## 🧪 Data Models & Domain
- **Asset:** The master reference media protected by the rights holder.
- **ScanJob:** A specific operation targeting a search query across platforms.
- **ScrapedVideo:** Suspect media discovered by the scraper nodes.
- **DetectionResult:** The analytical comparison between a `ScrapedVideo` and an `Asset`.
- **JudgeReview:** Operator-level verification for `REVIEW` status detections.
