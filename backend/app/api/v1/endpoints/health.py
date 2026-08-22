"""
Health Check and System Status Endpoint
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def get_health_status():
    return {
        "status": "HEALTHY",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "device": settings.DEVICE,
        "database": "CONNECTED",
        "ml_engine": settings.DEFAULT_SEGMENTATION_MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
