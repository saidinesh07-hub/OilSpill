"""
Temporal Evolution and Track Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.detections import SpillDetectionResponse


class TemporalObservationBase(BaseModel):
    track_id: str
    detection_id: str
    observation_time: datetime
    area_km2: float
    area_delta_km2: float = 0.0
    centroid_displacement_m: float = 0.0
    observed_state: str  # "EXPANSION", "CONTRACTION", "FRAGMENTATION", "PERSISTENCE", "DISAPPEARANCE"
    advection_iou_match: float = 1.0
    notes: Optional[str] = None


class TemporalObservationResponse(TemporalObservationBase):
    id: str
    detection: Optional[SpillDetectionResponse] = None
    model_config = ConfigDict(from_attributes=True)


class TrackedSlickBase(BaseModel):
    slick_name: str
    first_seen: datetime
    last_seen: datetime
    current_status: str = "ACTIVE"
    total_area_km2: float = 0.0
    current_centroid_lat: Optional[float] = None
    current_centroid_lon: Optional[float] = None
    drift_speed_kmh: float = 0.0
    drift_heading_deg: float = 0.0
    growth_rate_km2_per_hr: float = 0.0
    latest_detection_id: Optional[str] = None


class TrackedSlickResponse(TrackedSlickBase):
    track_id: str
    created_at: datetime
    updated_at: datetime
    temporal_observations: List[TemporalObservationResponse] = []
    model_config = ConfigDict(from_attributes=True)
