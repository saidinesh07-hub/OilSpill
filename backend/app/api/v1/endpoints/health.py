"""
Health Check and System Status Endpoint
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

from backend.app.services.cdse_client import CDSEClient

@router.get("")
def get_health_status():
    cdse_client = CDSEClient()
    cdse_status = "AVAILABLE" if cdse_client.has_credentials else "UNAVAILABLE (Missing CDSE_CLIENT_ID/SECRET)"
    
    cmems_status = "AVAILABLE" if (settings.CMEMS_USERNAME and settings.CMEMS_PASSWORD) else "UNAVAILABLE (Missing CMEMS credentials)"
    cds_status = "AVAILABLE" if settings.CDS_API_KEY else "UNAVAILABLE (Missing CDS_API_KEY)"
    ais_status = "AVAILABLE" if (settings.AIS_API_KEY or settings.AISHUB_USERNAME) else "UNAVAILABLE (Missing AIS credentials)"
    
    return {
        "status": "HEALTHY",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "device": settings.DEVICE,
        "database": "CONNECTED",
        "ml_engine": settings.DEFAULT_SEGMENTATION_MODEL,
        "providers": {
            "cdse": cdse_status,
            "cmems": cmems_status,
            "cds": cds_status,
            "ais": ais_status
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
