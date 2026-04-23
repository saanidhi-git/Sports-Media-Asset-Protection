import cv2
import gc
import imagehash
import logging
import numpy as np
import os
import shutil
import subprocess

from PIL import Image

logger = logging.getLogger(__name__)


def get_phash(cv2_image: np.ndarray) -> str | None:
    """
    Generates a perceptual hash (pHash) for an OpenCV frame.
    Explicitly releases the PIL image from memory after hashing.
    """
    try:
        rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        result = str(imagehash.phash(pil_image))
        pil_image.close()
        del rgb, pil_image
        gc.collect()
        return result
    except Exception as e:
        logger.warning(f"pHash generation failed: {e}")
        return None


def get_pdq(cv2_image: np.ndarray) -> str | None:
    """
    Generates a Meta PDQ hash for an OpenCV frame.
    Returns a 64-character hex string (256-bit hash).
    Explicitly releases intermediate arrays from memory.
    """
    try:
        import pdqhash  # late import — optional dependency
        rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        hash_vector, _quality = pdqhash.compute(rgb)
        byte_array = np.packbits(hash_vector)
        result = byte_array.tobytes().hex()
        del rgb, hash_vector, byte_array
        gc.collect()
        return result
    except ImportError:
        logger.warning("pdqhash not installed. PDQ fingerprinting skipped.")
        return None
    except Exception as e:
        logger.warning(f"PDQ generation failed: {e}")
        return None


def get_audio_fp(video_path: str) -> str | None:
    """
    Computes the Chromaprint audio fingerprint using fpcalc.
    Gracefully skips if fpcalc binary is not installed.
    """
    if not os.path.exists(video_path):
        logger.warning(f"get_audio_fp: video not found at {video_path}")
        return None

    if shutil.which("fpcalc") is None:
        logger.warning("fpcalc binary not found on PATH. Audio fingerprinting disabled.")
        return None

    try:
        result = subprocess.run(
            ["fpcalc", "-raw", "-length", "60", video_path],
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        for line in result.stdout.splitlines():
            if line.startswith("FINGERPRINT="):
                return line.split("=", 1)[1]
        logger.warning("fpcalc returned no FINGERPRINT line.")
    except subprocess.TimeoutExpired:
        logger.warning(f"fpcalc timed out for {video_path}")
    except Exception as e:
        logger.warning(f"Audio fingerprinting failed for {video_path}: {e}")

    return None
