"""
Common Schemas and Base Models
"""
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any]
    id: Optional[str] = None

class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
