"""
Environmental and MetOcean Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class EnvironmentalSnapshotBase(BaseModel):
    variable: str  # "ocean_currents_uv", "surface_wind_uv", "waves_stokes_drift"
    source: str
    valid_time: datetime
    data_vintage: datetime
    bbox: List[float]
    u_mean: float = 0.0
    v_mean: float = 0.0
    magnitude_mean: float = 0.0
    grid_data: Optional[Dict[str, Any]] = None
    storage_path: Optional[str] = None


class EnvironmentalSnapshotResponse(EnvironmentalSnapshotBase):
    snapshot_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
