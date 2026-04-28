"""
SPORTS GUARDIAN — RT-DETRv2 Object Detection Microservice
Designed for standalone deployment on Render / Railway / Docker.

Model weights are downloaded on startup from a configurable URL,
keeping the Docker image and Git repo lightweight.
"""

import logging
import os
import requests
import cv2
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# ── LOGGING ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("ModelService")

app = FastAPI(
    title="SPORTS GUARDIAN RT-DETRv2 Detection Service",
    version="1.0.0",
)

# ══════════════════════════════════════════════════════════════════════
#  CONFIG — Set these via Environment Variables on Render
# ══════════════════════════════════════════════════════════════════════
# Option 1: Auto-download from a URL (HuggingFace, Google Drive, Cloudinary)
# Example: https://huggingface.co/user/model/resolve/main/rtdetrv2-l.pt
MODEL_DOWNLOAD_URL = os.getenv("MODEL_DOWNLOAD_URL", "")

# Option 2: Use a local path (if weights are baked into the Docker image)
WEIGHTS_DIR = Path("weights")
MODEL_FILENAME = os.getenv("MODEL_FILENAME", "rtdetrv2-l.pt")
MODEL_PATH = WEIGHTS_DIR / MODEL_FILENAME

# Confidence threshold for inference
DEFAULT_CONFIDENCE = float(os.getenv("DEFAULT_CONFIDENCE", "0.25"))

# ══════════════════════════════════════════════════════════════════════

# Global model instance
model = None


def download_weights():
    """
    Downloads model weights from MODEL_DOWNLOAD_URL if they don't exist locally.
    Supports: HuggingFace, Google Drive (direct links), Cloudinary, any direct URL.
    """
    if MODEL_PATH.exists():
        logger.info(f"✅ Weights already exist at {MODEL_PATH}")
        return True

    if not MODEL_DOWNLOAD_URL:
        logger.warning(
            "⚠️ No MODEL_DOWNLOAD_URL set and no local weights found. "
            "Ultralytics will attempt to download default COCO weights."
        )
        return True  # Let ultralytics handle it

    logger.info(f"📥 Downloading weights from: {MODEL_DOWNLOAD_URL}")
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(MODEL_DOWNLOAD_URL, stream=True, timeout=300)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(MODEL_PATH, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = (downloaded / total) * 100
                    if downloaded % (1024 * 1024) < 8192:  # Log every ~1MB
                        logger.info(f"   ↓ {downloaded / 1e6:.1f} MB / {total / 1e6:.1f} MB ({pct:.0f}%)")

        logger.info(f"✅ Weights saved to {MODEL_PATH} ({MODEL_PATH.stat().st_size / 1e6:.1f} MB)")
        return True
    except Exception as e:
        logger.error(f"❌ Weight download failed: {e}")
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()  # Remove partial download
        return False


@app.on_event("startup")
def load_model():
    global model
    download_weights()

    logger.info(f"🚀 Loading RT-DETRv2 model...")
    try:
        from ultralytics import RTDETR

        # If local weights exist, use them. Otherwise let ultralytics fetch defaults.
        if MODEL_PATH.exists():
            model = RTDETR(str(MODEL_PATH))
        else:
            model = RTDETR(MODEL_FILENAME)  # e.g. "rtdetrv2-l.pt" → auto-download

        logger.info("✅ Model loaded and ready for inference.")
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")


# ── REQUEST / RESPONSE SCHEMAS ──

class PredictionRequest(BaseModel):
    image_url: str
    confidence_threshold: float = DEFAULT_CONFIDENCE

class Detection(BaseModel):
    label: str
    confidence: float
    box: List[float]  # [x1, y1, x2, y2]

class PredictionResponse(BaseModel):
    detections: List[Detection]
    frame_width: int
    frame_height: int


# ── ENDPOINTS ──

@app.get("/health")
def health_check():
    return {
        "status": "online" if model is not None else "degraded",
        "model_file": str(MODEL_PATH),
        "weights_exist": MODEL_PATH.exists(),
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Check /health.")

    try:
        logger.info(f"🔍 Analyzing frame: {request.image_url[:80]}...")

        # 1. Download frame from Cloudinary
        resp = requests.get(request.image_url, timeout=15)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to download image (HTTP {resp.status_code})",
            )

        # 2. Decode to OpenCV
        nparr = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode image data")

        h, w = img.shape[:2]

        # 3. Run RT-DETRv2 Inference
        results = model.predict(
            source=img,
            conf=request.confidence_threshold,
            save=False,
            verbose=False,
        )

        # 4. Parse detections
        detections = []
        for r in results:
            for box in r.boxes:
                b = box.xyxy[0].tolist()
                cls_id = int(box.cls[0])
                label = model.names[cls_id]
                conf = round(float(box.conf[0]), 4)

                detections.append(Detection(label=label, confidence=conf, box=b))

        logger.info(f"✅ {len(detections)} objects detected.")
        return PredictionResponse(detections=detections, frame_width=w, frame_height=h)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
