# SHIELD_MEDIA: Sports Media Asset Protection

A comprehensive system for registering and protecting sports media assets using advanced monitoring and anti-piracy protocols.

## Project Overview

SHIELD_MEDIA provides a secure vault and monitoring service for sports media rights holders. The platform allows users to:
- **Register Assets:** Securely upload media assets with metadata and automated frame extraction.
- **Automated Monitoring:** Configure scraping protocols for platforms like YouTube, Reddit, and Instagram.
- **Real-time Dashboard:** Monitor asset status, security levels, and system logs.
- **Identity Management:** Secure operator login and registration with JWT-based authentication.

## Technical Stack

### Backend
- **Framework:** FastAPI (Python 3.12)
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Migrations:** Alembic
- **Dependency Management:** UV
- **Authentication:** OAuth2 with JWT tokens and Bcrypt password hashing
- **File Storage:** Local upload management with unique UUID mapping

### Frontend
- **Framework:** Angular 19
- **State Management:** Angular Signals
- **Styling:** Vanilla CSS with a modern "Mission Control" aesthetic (Neon-themed)
- **Security:** Functional Auth Guards and HTTP Interceptors for token management

## Features Implemented

### Asset Management
- **Duplicate Prevention:** Backend validation prevents multiple registrations of the same asset name by a single user.
- **Optimized Uploads:** Asynchronous-capable file handling to prevent event-loop blocking during large transfers.
- **Asset Vault:** Real-time fetching of user-owned assets on the dashboard.

### Security
- **Authentication:** Complete sign-up and sign-in flow.
- **Protected Routes:** Frontend guards ensure only authenticated operators can access the dashboard and registration tools.
- **Concurrency Control:** UI-level protections (button disabling) to prevent race conditions and duplicate submissions.

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js (Latest LTS)
- PostgreSQL

### Backend Setup
1. Navigate to `/backend`
2. Install dependencies: `uv sync`
3. Configure `.env` file with your database credentials.
4. Run migrations: `alembic upgrade head`
5. Start server: `fastapi dev app/main.py`

### Frontend Setup
1. Navigate to `/frontend`
2. Install dependencies: `npm install`
3. Start development server: `npm start`
4. Access via `http://localhost:4200`

## System Architecture

The application follows a modular architecture:
- `backend/app/api`: API routes and dependency injection.
- `backend/app/db`: Database models and session management.
- `frontend/src/app/core`: Shared services, guards, and interceptors.
- `frontend/src/app/home`: Dashboard and asset overview.
- `frontend/src/app/register-asset`: Multi-step asset ingestion form.
