from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.database.session import get_db
from backend.app.schemas.common import APIResponse
from backend.app.services.maritime_service import MaritimeOrchestrator, MaritimeResponse

router = APIRouter(prefix="/maritime", tags=["Maritime Intelligence"])

@router.get("/vessels", response_model=APIResponse)
async def get_vessels(
    min_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    max_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    min_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    max_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    limit: int = Query(1000, ge=1, le=5000)
):
    has_bbox = any(v is not None for v in [min_lat, max_lat, min_lon, max_lon])
    
    if has_bbox and not all(v is not None for v in [min_lat, max_lat, min_lon, max_lon]):
        raise HTTPException(status_code=400, detail="Must provide all four bbox parameters or none.")
        
    if has_bbox:
        if min_lat > max_lat or min_lon > max_lon: # type: ignore
            raise HTTPException(status_code=400, detail="Invalid bbox coordinates. min must be <= max.")
            
    orchestrator = MaritimeOrchestrator()
    try:
        response = await orchestrator.get_vessels(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            limit=limit
        )
        # Ensure we return 200 OK with UNAVAILABLE inside if everything failed.
        # This prevents crashing the frontend while allowing graceful degradation.
        return APIResponse(data=response.model_dump())
    except Exception as e:
        # Never expose raw exception to frontend
        return APIResponse(
            success=False,
            data={
                "status": "UNAVAILABLE",
                "provider": None,
                "fallback_used": True,
                "vessel_count": 0,
                "vessels": []
            }
        )

@router.get("/spill/{spill_id}/vessels", response_model=APIResponse)
def correlate_spill_vessels(
    spill_id: str,
    db: Session = Depends(get_db)
):
    from backend.app.database.models import SpillDetection, VesselSnapshot
    from backend.app.services.source_correlation_service import correlate_sources
    from datetime import datetime, timezone
    
    detection = db.query(SpillDetection).filter(SpillDetection.detection_id == spill_id).first()
    if not detection:
        raise HTTPException(status_code=404, detail="Spill detection not found")
        
    spill_time = detection.created_at.isoformat() if detection.created_at else None
    
    # Temporal Window Configuration
    PRE_SPILL_HOURS = 24.0
    POST_SPILL_HOURS = 12.0
    
    # Spatial Filtering Configuration
    # Bounding envelope buffer for candidate filtering before exact geodesic calculations
    search_radius_km = 35.0
    lat_margin = search_radius_km / 111.0
    import math
    try:
        lon_margin = search_radius_km / (111.0 * math.cos(math.radians(detection.centroid_lat)))
    except Exception:
        lon_margin = lat_margin
    
    from datetime import timedelta
    t_start = detection.created_at - timedelta(hours=PRE_SPILL_HOURS)
    t_end = detection.created_at + timedelta(hours=POST_SPILL_HOURS)
    
    # Coarse candidate filtering using bounding envelope and temporal window
    history_vessels = db.query(VesselSnapshot).filter(
        VesselSnapshot.latitude >= detection.centroid_lat - lat_margin,
        VesselSnapshot.latitude <= detection.centroid_lat + lat_margin,
        VesselSnapshot.longitude >= detection.centroid_lon - lon_margin,
        VesselSnapshot.longitude <= detection.centroid_lon + lon_margin,
        VesselSnapshot.ais_timestamp >= t_start,
        VesselSnapshot.ais_timestamp <= t_end
    ).all()
    
    vessel_dicts = []
    for v in history_vessels:
        vessel_dicts.append({
            "mmsi": v.mmsi,
            "name": v.name,
            "latitude": v.latitude,
            "longitude": v.longitude,
            "vessel_type": v.vessel_type,
            "timestamp": v.ais_timestamp.isoformat() if v.ais_timestamp else None,
            "speed": v.speed_knots,
            "course": v.course_deg,
            "source": v.provider,
            "freshness": v.freshness_status
        })
        
    correlation_result = correlate_sources(
        spill_lat=detection.centroid_lat,
        spill_lon=detection.centroid_lon,
        spill_time=spill_time,
        spill_geojson=detection.geom_geojson,
        vessels=vessel_dicts
    )
    
    return APIResponse(
        data={
            "spill_id": spill_id,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "candidates": correlation_result.get("candidates", [])
        }
    )

