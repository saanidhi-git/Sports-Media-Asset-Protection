# 🛡️ SPORTS GUARDIAN: Advanced Sports Media Asset Protection

**SPORTS GUARDIAN** is a high-performance, anti-piracy ecosystem designed for sports media rights holders. It provides a "Mission Control" interface to register protected assets, deploy scraping nodes across social platforms, and identify copyright infringements using multi-modal fingerprinting (Visual, Audio, and Scoreboard OCR).

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Angular](https://img.shields.io/badge/Frontend-Angular%2019-DD0031?style=for-the-badge&logo=angular&logoColor=white)](https://angular.dev/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Neo-Brutalism](https://img.shields.io/badge/UI_Style-Neo--Brutalism-FFD700?style=for-the-badge)](https://web.dev/articles/neo-brutalism-design)

---

## 🚀 Core Features

### 1. Asset Vault (Digital Fingerprinting)
- **Ingestion:** Upload master sports media (clips, match highlights).
- **Multi-Modal Hashing:** Generates `pHash` (Perceptual) and `PDQ` (Geometric) vectors for visual matching resistant to resizing and cropping.
- **Acoustic Fingerprinting:** Audio-based detection for streams with obscured video.

### 2. Radar Operations (Scanning Pipeline)
- **Distributed Scraping:** Nodes targeting YouTube, Instagram, and Reddit using `yt-dlp` and official APIs.
- **Real-time Discovery:** Search-based discovery (e.g., "Live Match Stream") with frame-buffer analysis.
- **Live Terminal:** Real-time feedback of scraping and analysis progress.

### 3. Verdict Engine (AI & CV Moderation)
- **Scoreboard OCR:** Uses YOLO-based detection (RT-DETRv2) to sync match time/score with the master asset.
- **AI Moderator:** Agentic reasoning using Gemini Pro (`google/gemini-pro-latest`) to analyze metadata and piracy signals.
- **Human-in-the-Loop:** A dedicated review queue for moderate-confidence detections.

### 4. Enforcement & Audit
- **Notice Generation:** Automated creation of copyright infringement notices.
- **Blockchain Proof:** Immutable anchoring of asset fingerprints for legal enforcement.

### 5. Authentication & Security (JWT)
- **OAuth2 with Password Flow:** Secure login using `FastAPI` and `JOSE` JWT tokens.
- **Role-Based Access:** Protected API endpoints and frontend guards to ensure only authorized operators can manage assets and scans.
- **Bcrypt Hashing:** Industry-standard password encryption for user security.
- **Token-Based Interceptor:** Angular interceptor automatically attaches JWT tokens to outgoing API requests for seamless, secure communication.

---

## 📸 Visual Tour

### 🖥️ Mission Control (Dashboard)
Overview of protected assets, active scan jobs, and threat levels.
![Dashboard](screenshot/dash_board.png)

### 📥 Asset Registration
Securely upload and fingerprint master media assets.
![Register Asset](screenshot/register-asset.png)

### 🔍 Active Scan Terminal
Initiate and monitor real-time scraping operations across social platforms.
![Scan Page](screenshot/scan_page.png)

### 📊 Detection Analysis
Detailed breakdown of matches found, including similarity scores and visual comparisons.
![Scan Result](screenshot/scan_result.png)

### ⚖️ Review Queue
Operators can manually verify flagged content before enforcement actions.
![Human Review Queue](screenshot/human_review_quee.png)

### 📜 Enforcement
Automated generation of copyright notices and takedown reports.
![Copyright Notice](screenshot/copyright_isuue_notice_gen.png)

---

## 🛠️ Technical Stack

| Component | Technologies |
| :--- | :--- |
| **Backend** | FastAPI, SQLAlchemy, LangGraph, OpenCV, ImageHash, PDQHash, yt-dlp |
| **Frontend** | Angular 19+, Signals, Standalone Components, Neo-Brutalism UI |
| **CV Model** | RT-DETRv2, Ultralytics, FastAPI (Microservice) |
| **Database** | PostgreSQL, Alembic |
| **AI/LLM** | Gemini Pro (`google/gemini-pro-latest`), Ollama |

---

## ⚙️ Installation & Setup

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **PostgreSQL**
- **FFMPEG** (for media processing)

### 1. Backend Setup
```bash
cd backend
# Install dependencies using UV
uv sync

# Configure Environment
# Create a .env file based on the requirements
# DATABASE_URL=postgresql://user:password@localhost/shield_media

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
*Access the UI at `http://localhost:4200`*

### 3. Model Service (Detection)
```bash
cd model
pip install -r requirements.txt
python main.py
```
*Runs on `http://localhost:8001` by default.*

---

## 📖 How To Use

1.  **Login:** Access the Mission Control terminal via the [Login Page](screenshot/login_register_page.png).
2.  **Register Asset:** Go to "Register Asset" and upload your master match clip. The system will automatically generate visual and audio fingerprints.
3.  **Start a Scan:** Navigate to "New Scan", enter search queries (e.g., "Team A vs Team B Live"), and select the platforms to monitor.
4.  **Monitor Progress:** Use the [Scan History](screenshot/scan_history_page.png) to track active jobs in real-time.
5.  **Review Detections:** Check the "Human Review" queue for any content flagged with a `REVIEW` status.
6.  **Take Action:** For `FLAGGED` content, view the [Scan Result](screenshot/scan_result.png) and generate an automated [Copyright Notice](screenshot/copyright_isuue_notice_gen.png).

---

## 📂 Project Structure

```text
├── backend/            # FastAPI Application & Business Logic
├── frontend/           # Angular 19+ Neo-Brutalism UI
├── model/              # RT-DETRv2 Object Detection Service
├── screenshot/         # Application Screenshots
└── Detailed_Technical_Documentation.md # Full architecture deep-dive
```

---

## 📜 License
Internal Project - All Rights Reserved.
