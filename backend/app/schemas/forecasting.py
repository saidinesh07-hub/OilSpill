"""
Trajectory Forecasting Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ForecastBandResponse(BaseModel):
    id: str
    forecast_run_id: str
    horizon_hours: int  # 6, 12, 24, 48
    target_time: datetime
    confidence_level: float  # 0.50, 0.80, 0.95
    geom_geojson: Dict[str, Any]
    area_km2: float
    centroid_lat: float
    centroid_lon: float
    mean_speed_kmh: float
    model_config = ConfigDict(from_attributes=True)


class ForecastRunRequest(BaseModel):
    track_id: str
    ensemble_size: int = 50
    horizons_hours: List[int] = [6, 12, 24, 48]
    wind_drift_factor: float = 0.03
    wind_deflection_angle_deg: float = 15.0
    diffusion_coefficient: float = 2.0


class ForecastRunResponse(BaseModel):
    forecast_run_id: str
    track_id: str
    run_time: datetime
    engine: str
    engine_version: str
    ensemble_size: int
    wind_drift_factor: float
    wind_deflection_angle_deg: float
    diffusion_coefficient: float
    confidence_decay_rate: float
    summary: Dict[str, Any] = {}
    bands: List[ForecastBandResponse] = []
    model_config = ConfigDict(from_attributes=True)
