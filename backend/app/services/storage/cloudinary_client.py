import cloudinary
import cloudinary.uploader
import cloudinary.api
from app.core.config import settings
import logging
import os
import re

logger = logging.getLogger(__name__)

# Initialize Cloudinary
if settings.CLOUDINARY_URL and settings.CLOUDINARY_URL.startswith("cloudinary://"):
    try:
        # Manually parse to ensure correct config
        pattern = r"cloudinary://([^:]+):([^@]+)@(.+)"
        match = re.match(pattern, settings.CLOUDINARY_URL)
        if match:
            key, secret, name = match.groups()
            cloudinary.config(
                cloud_name=name,
                api_key=key,
                api_secret=secret,
                secure=True
            )
            logger.info(f"📡 Cloudinary configured for cloud: {name}")
        else:
            # Fallback to default parsing
            cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
    except Exception as e:
        logger.error(f"Failed to parse CLOUDINARY_URL: {e}")
else:
    logger.warning("CLOUDINARY_URL not found or invalid in settings.")

def upload_image(file_path: str, folder: str = "sports-guardian/frames") -> str:
    """Uploads an image to Cloudinary and returns the secure URL."""
    try:
        response = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            resource_type="image",
            use_filename=True,
            unique_filename=True
        )
        return response.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary image upload failed: {e}")
        raise

def upload_auto(file_path: str, folder: str = "sports-guardian/raw") -> str:
    """Uploads any file type (PDF, TXT, etc.) to Cloudinary with automatic type detection."""
    try:
        response = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            resource_type="auto"
        )
        return response.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary auto upload failed: {e}")
        raise

def upload_video(file_path: str, folder: str = "sports-guardian/assets") -> str:
    """Uploads a video to Cloudinary and returns the secure URL."""
    try:
        response = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            resource_type="video",
            chunk_size=6000000 # 6MB chunks for large files
        )
        return response.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary video upload failed: {e}")
        raise

def delete_asset(public_id: str, resource_type: str = "image"):
    """Deletes an asset from Cloudinary."""
    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
    except Exception as e:
        logger.error(f"Cloudinary deletion failed for {public_id}: {e}")

def delete_asset_by_url(url: str):
    """
    Extracts public_id from a Cloudinary URL and deletes it.
    Works for both images and videos.
    """
    if not url or "res.cloudinary.com" not in url:
        return

    try:
        # Cloudinary URL format: https://res.cloudinary.com/<cloud_name>/<resource_type>/upload/v<version>/<folder>/<public_id>.<ext>
        # We need the part after 'upload/v<version>/' and before the extension.
        
        resource_type = "video" if "/video/upload/" in url else "image"
        
        # Regex to find everything between the version (v123456789/) and the extension
        pattern = r"/upload/v\d+/(.+)\.[a-z0-9]+$"
        match = re.search(pattern, url)
        if match:
            public_id = match.group(1)
            delete_asset(public_id, resource_type=resource_type)
            logger.info(f"🗑️ Cloudinary asset deleted: {public_id} ({resource_type})")
    except Exception as e:
        logger.error(f"Failed to delete Cloudinary asset by URL {url}: {e}")
