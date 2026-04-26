"""
Sports Guardian AI — FastAPI Application Entry Point
"""
import os
import logging
import time
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.job_logging import setup_job_logging
from app.db.session import SessionLocal, engine
from app.api.deps import get_db
from app.core.config import settings

# Initialize the custom thread-local job logger
setup_job_logging()
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)

app = FastAPI(
    title="Sports Guardian AI",
    description="Modular sports media protection API: Register assets, detect piracy, judge & act.",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (serve extracted frames to the frontend) ───────────────────
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── API v1 router ────────────────────────────────────────────────────────────
app.include_router(api_v1_router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "Sports Guardian AI v6.0"}


@app.get("/health", tags=["Health"])
@app.get("/health/matrix", tags=["Health"])
def health(db: Session = Depends(get_db)):
    """
    Detailed system health matrix to monitor stability and configuration.
    Helps prevent crashes in development by verifying all subsystems.
    """
    health_matrix = {
        "status": "operational",
        "timestamp": time.time(),
        "components": {
            "database": {"status": "unknown"},
            "smtp": {"status": "unknown"},
            "storage": {"status": "unknown"},
        }
    }

    # 1. Check Database
    try:
        db.execute(text("SELECT 1"))
        health_matrix["components"]["database"] = {
            "status": "healthy",
            "latency_ms": "n/a" # Simple check
        }
    except Exception as e:
        health_matrix["status"] = "degraded"
        health_matrix["components"]["database"] = {
            "status": "error",
            "detail": str(e)
        }

    # 2. Check SMTP Config
    is_smtp_configured = all([
        settings.SMTP_HOST,
        settings.SMTP_USER,
        settings.SMTP_PASS,
        settings.EMAILS_FROM_EMAIL
    ])
    health_matrix["components"]["smtp"] = {
        "status": "healthy" if is_smtp_configured else "unconfigured",
        "host": settings.SMTP_HOST or "none"
    }

    # 3. Check Storage (Uploads directory)
    try:
        test_file = os.path.join(UPLOAD_DIR, ".health_check")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        health_matrix["components"]["storage"] = {
            "status": "healthy",
            "path": os.path.abspath(UPLOAD_DIR)
        }
    except Exception as e:
        health_matrix["status"] = "degraded"
        health_matrix["components"]["storage"] = {
            "status": "error",
            "detail": str(e)
        }

    return health_matrix
