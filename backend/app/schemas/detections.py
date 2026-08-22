"""
Spill Detection Schemas
"""
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class SpillDetectionBase(BaseModel):
    observation_id: str
    geom_geojson: Dict[str, Any]
    centroid_lat: float
    centroid_lon: float
    area_km2: float
    perimeter_km: float
    predicted_class: str  # "oil_spill", "look_alike", "ship", "land", "sea_surface"
    confidence: float
    lookalike_risk_score: float = 0.0
    morphology_features: Dict[str, Any] = {}
    model_version: str


class SpillDetectionCreate(SpillDetectionBase):
    pass


class SpillDetectionResponse(SpillDetectionBase):
    detection_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
