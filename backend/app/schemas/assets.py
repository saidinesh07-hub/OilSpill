"""
Asset Layer Schemas
"""
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class AssetBase(BaseModel):
    name: str
    asset_type: str  # "protected_area", "fishery", "port", "beach", "wetland", "coastal_population"
    geom_geojson: Dict[str, Any]
    centroid_lat: float
    centroid_lon: float
    sensitivity_weight: float = 1.0
    data_source: str = "WDPA / OSM / GFW"
    data_vintage: datetime
    properties: Dict[str, Any] = {}


class AssetCreate(AssetBase):
    pass


class AssetResponse(AssetBase):
    asset_id: str
    model_config = ConfigDict(from_attributes=True)
