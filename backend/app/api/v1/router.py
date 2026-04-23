"""v1 API router — aggregates all domain routers."""
from fastapi import APIRouter

from app.api.v1 import auth, assets, pipeline, review, notice

router = APIRouter()

router.include_router(auth.router)
router.include_router(assets.router)
router.include_router(pipeline.router)
router.include_router(review.router)
router.include_router(notice.router)
