# SHIELD_MEDIA - Sports Media Asset Protection

A high-fidelity media asset protection and monitoring system featuring a sleek, cyber-industrial UI and a modular, production-grade FastAPI backend.

## Architecture Overview

The system is built with a decoupled architecture to ensure scalability and operational security:

- **Frontend**: Angular 19 SPA with a high-performance "Cyber-Industrial" dashboard.
- **Backend**: FastAPI (Python 3.12+) with a domain-driven modular structure.
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations.

## Key Features

- **Mission Control Dashboard**: Real-time overview of active nodes, security status, and system logs.
- **Secure Asset Registration**:
  - Operational control panel for media ingestion.
  - Dual-file upload support (Media Assets & Scoreboard/Match Data).
  - Automated keyframe extraction preview.
  - Configurable monitoring pipeline for **YouTube**, **Reddit**, and **Instagram**.
- **Modular Pipeline**: Extensible architecture for fingerprinting (pHash, PDQ), automated scoring, and AI-driven decision engines.

## Tech Stack

### Frontend
- **Framework**: Angular 19 (Standalone Components)
- **Styling**: Vanilla CSS with custom design tokens (Neon accents, dark-mode first).
- **Tooling**: API Proxy configuration for production-grade development.

### Backend
- **Framework**: FastAPI
- **Config**: Pydantic Settings for secure environment management.
- **ORM**: SQLAlchemy 2.0 with a flexible Base Class architecture.
- **Database**: PostgreSQL (`sport_media_protection_DB`).

---

## Getting Started

### Prerequisites
- **Node.js**: v22.19.0+
- **Python**: 3.12+
- **PostgreSQL**: Local instance running.

### 1. Database Setup
Create a PostgreSQL database named `sport_media_protection_DB`.

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
pip install -r requirements.txt # Or use 'uv sync'
```
Create a `.env` file in the `backend/` directory:
```env
POSTGRES_SERVER=localhost
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=sport_media_protection_DB
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

---

## Running the Application

### Start Backend
```bash
cd backend
uvicorn app.main:app --reload
```
The API is proxied through the frontend for a seamless development experience.

### Start Frontend
```bash
cd frontend
npm start
```
*Access the application at http://localhost:4200*

---

## Project Structure

```text
backend/
├── app/
│   ├── api/routes/    # Domain-specific endpoints
│   ├── core/          # App configuration
│   ├── db/            # Database session & models
│   ├── services/      # Business logic (Scrapers, Pipeline)
│   └── main.py        # Entry point
frontend/
├── src/app/
│   ├── home/          # Mission Control Dashboard
│   ├── register-asset/# Asset Ingestion Page
│   └── login-register/# Authentication Gateway
└── proxy.conf.json    # API Proxy configuration
```
