"""
Environmental MetOcean Endpoints
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.environmental.cmems_adapter import CMEMSAdapter
from backend.app.environmental.era5_gfs_adapter import WindForcingAdapter
from backend.app.schemas.common import APIResponse

router = APIRouter(prefix="/environmental", tags=["Environmental MetOcean"])


@router.get("/metocean_summary")
def get_metocean_summary(
    min_lon: float = 80.20,
    min_lat: float = 13.00,
    max_lon: float = 80.50,
    max_lat: float = 13.45
):
    bbox = [min_lon, min_lat, max_lon, max_lat]
    now = datetime.now(timezone.utc)
    cmems = CMEMSAdapter()
    wind = WindForcingAdapter()

    curr = cmems.get_surface_currents(bbox, now)
    w = wind.get_surface_winds(bbox, now)
    stokes = cmems.get_stokes_drift(bbox, now)

    return APIResponse(data={
        "ocean_currents": curr,
        "surface_winds": w,
        "wave_stokes_drift": stokes
    })
