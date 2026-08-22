"""
Satellite Scene and Observation Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class SatelliteSceneBase(BaseModel):
    scene_name: str
    source: str = "Sentinel-1 SAR"
    sensor_mode: str = "IW"
    polarization: List[str] = ["VV", "VH"]
    acquisition_time: datetime
    footprint_geojson: Dict[str, Any]
    bbox: List[float]
    incidence_angle_min: Optional[float] = None
    incidence_angle_max: Optional[float] = None
    storage_path: Optional[str] = None
    is_synthetic: bool = False
    ingestion_status: str = "COMPLETED"


class SatelliteSceneCreate(SatelliteSceneBase):
    pass


class SatelliteSceneResponse(SatelliteSceneBase):
    scene_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ObservationBase(BaseModel):
    scene_id: str
    preprocessing_version: str = "v1.0-lee-filter-sigma0"
    tile_grid_id: Optional[str] = None
    raster_metadata: Dict[str, Any] = {}


class ObservationResponse(ObservationBase):
    observation_id: str
    processed_at: datetime
    scene: Optional[SatelliteSceneResponse] = None
    model_config = ConfigDict(from_attributes=True)
