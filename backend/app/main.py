"""
Sports Guardian AI — FastAPI Application Entry Point
"""
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.job_logging import setup_job_logging

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
    allow_origins=["http://localhost:4200"],
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
def health():
    return {"status": "healthy"}
