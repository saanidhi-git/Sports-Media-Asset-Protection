# 🛡️ Sports Guardian AI: Master Technical Documentation & Implementation Plan

## 1. Executive Summary
**Sports Guardian AI** is an advanced, multi-agentic ecosystem designed to protect high-value sports media assets in real-time. By combining **Local Scraping Nodes**, **Two-Agent AI Orchestration (Gemini 2.0)**, **Computer Vision (YOLO/OCR)**, and **Blockchain Proof-of-Ownership**, the system closes the critical "Match Over" gap where $28B in revenue is lost annually to piracy.

---

## 2. System Architecture: The "Node-to-Node" Kundli

### 2.1 High-Level Overview
The system operates as a distributed network of specialized nodes:
1.  **The Asset Vault:** Secure registration and fingerprinting of master assets.
2.  **Local Scraping Nodes:** High-velocity, disk-less extraction from social platforms.
3.  **Agentic Analysis Engine:** The "Two-Agent" brain that verifies and reasons.
4.  **Enforcement Registry:** Blockchain-backed action and audit logging.

### 2.2 Component Breakdown

#### A. Backend (The Orchestrator)
*   **Framework:** FastAPI (Python 3.12+).
*   **State Management:** LangGraph for agentic workflow orchestration.
*   **Database:** PostgreSQL with SQLAlchemy ORM.
*   **Task Queue:** Background tasks for asynchronous stream analysis.

#### B. Frontend (Mission Control)
*   **Framework:** Angular 19+ (Standalone Components, Signals).
*   **UI Paradigm:** Neo-Brutalism (High-contrast, high-impact visibility).
*   **Real-time Feedback:** Live terminal tracking of scraping progress.

---

## 3. The Technical Pillars (Deep Dive)

### 3.1 Pillar 1: Local Scraping Engine
*   **Concept:** Disk-less, stream-based extraction.
*   **Workflow:**
    1.  Fetch direct stream URLs (HLS/Dash) using `yt-dlp`.
    2.  Capture frame buffers directly from the network stream using `FFMPEG` pipe.
    3.  Extract 30s audio chunks for acoustic fingerprinting.
*   **Advantage:** Bypasses anti-bot measures by avoiding high-volume file downloads.

### 3.2 Pillar 2: Multi-Modal Fingerprinting
*   **Visual Hashing:**
    *   **pHash (Perceptual Hash):** Resistant to compression and color changes.
    *   **PDQ Hash (Meta Standard):** Resistant to geometric transformations (cropping, mirroring, rotation).
*   **Acoustic Fingerprinting:** Catching streams where the video is 100% obscured but the audio remains authentic.

### 3.3 Pillar 3: Computer Vision (YOLO + OCR)
*   **Target:** The Scoreboard.
*   **Process:**
    1.  **YOLO Detection:** Identify the scoreboard bounding box in dynamic broadcast layouts.
    2.  **OCR Extraction:** Extract match time, score, and teams using Tesseract/PaddleOCR.
    3.  **Temporal Matching:** Compare extracted data against the Master Asset's timeline. Match found if `Score + Time` syncs with the vault record.

### 3.4 Pillar 4: Two-Agent AI Architecture
*   **Agent 1: The Moderator (Context Analysis):**
    *   Uses Gemini 2.0 Flash to analyze metadata + comments.
    *   **Chain of Reaction:** Registered Asset -> Content Comparison -> Audience Signals -> Verdict.
*   **Agent 2: The Enforcer (Action Taking):**
    *   Verifies ownership via the blockchain.
    *   Generates automated takedown reports or micro-licensing offers.

### 3.5 Pillar 5: Blockchain Proof of Ownership
*   **Mechanism:** Anchor the `Asset_ID + Fingerprint_Root` to a ledger.
*   **Purpose:** Immutable proof for legal enforcement and automated smart-contract licensing.

---

## 4. Operational Workflow (Sequence)

1.  **Ingestion:** User uploads a match highlight (e.g., "IPL Final Over").
2.  **Fingerprinting:** Vault generates PDQ/pHash/Audio fingerprints and anchors them to the Blockchain.
3.  **Discovery:** Scrapers search Reddit/YouTube for "IPL Live" or "Final Over."
4.  **Local Scraping:** Nodes extract frames and scoreboard data from found streams.
5.  **Agentic Review:**
    *   *CV Layer:* Checks scoreboard sync.
    *   *AI Layer:* Confirms audience excitement/piracy signals.
6.  **Enforcement:** High-confidence match triggers Agent 2 to file an automated report.

---

## 5. Performance & Impact Metrics

*   **Detection Speed:** <30 seconds from stream discovery to verdict.
*   **Real-time Accuracy:** >95% confidence through multi-modal cross-verification.
*   **Scalability:** 100+ concurrent scraping nodes per scan job.
*   **ROI:** Closing the $28B gap by reclaiming live-stream value for rights holders.

---

## 6. Implementation Roadmap

*   **Phase 1: The Vault:** pHash/PDQ implementation and Blockchain anchoring.
*   **Phase 2: The Radar:** Local Scraping engine for HLS stream extraction.
*   **Phase 3: The Brain:** YOLO scoreboard detection and Gemini 2.0 integration.
*   **Phase 4: The Enforcer:** LangGraph orchestration and automated reporting.
*   **Phase 5: Mission Control:** Neo-Brutalism UI integration for real-time tracking.
