from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from backend.app.schemas.common import APIResponse
from backend.app.services.cdse_client import CDSEClient

router = APIRouter(prefix="/satellite", tags=["Satellite"])

class SatelliteSearchRequest(BaseModel):
    latitude: float
    longitude: float
    start_date: datetime
    end_date: datetime
    mode: str = "DEMO"

@router.post("/search")
def search_satellite(request: SatelliteSearchRequest):
    if request.mode == "REAL":
        client = CDSEClient()
        if not client.has_credentials:
            return APIResponse(success=False, data={"reason": "REAL SATELLITE DATA TEMPORARILY UNAVAILABLE"})
        
        # Calculate a small bounding box around the coordinates (approx 1 degree)
        bbox = [request.longitude - 0.5, request.latitude - 0.5, request.longitude + 0.5, request.latitude + 0.5]
        
        result = client.search_sentinel1(
            bbox=bbox,
            start=request.start_date,
            end=request.end_date
        )
        
        if result.get("data_mode") == "UNAVAILABLE" or result.get("data_mode") == "ERROR":
             return APIResponse(success=False, data={"reason": f"REAL DATA UNAVAILABLE. {result.get('message', 'Search failed.')}"})
        
        return APIResponse(data=result.get("products", []))
    
    # Return mock demo scenes
    return APIResponse(data=[
        {
            "scene_id": "S1A_IW_GRDH_1SDV_20170128T002341",
            "source": "Sentinel-1A",
            "acquisition_time": request.start_date.isoformat(),
            "polarization": ["VV", "VH"],
            "sensor_mode": "IW",
            "is_synthetic": True,
            "data_mode": "DEMO_DATA"
        }
    ])
