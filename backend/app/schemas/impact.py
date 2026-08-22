"""
Impact Assessment Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.assets import AssetResponse


class ImpactAssessmentBase(BaseModel):
    forecast_run_id: str
    asset_id: str
    horizon_hours: int
    impact_probability: float
    earliest_time_to_impact_hours: float
    distance_to_slick_km: float
    intersected_area_km2: float = 0.0
    exposure_level: str  # "CRITICAL", "HIGH", "MODERATE", "LOW", "NEGLIGIBLE"


class ImpactAssessmentResponse(ImpactAssessmentBase):
    id: str
    created_at: datetime
    asset: Optional[AssetResponse] = None
    model_config = ConfigDict(from_attributes=True)
