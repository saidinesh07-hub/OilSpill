"""Normalized intelligence schemas with provenance and freshness."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProviderStatus(BaseModel):
    provider: str
    available: bool
    status: str  # OK | UNAVAILABLE | ERROR | DEMO | EMPTY
    message: str
    retrieved_at: datetime = Field(default_factory=utcnow)
    http_status: Optional[int] = None
    data_status: str = "UNAVAILABLE"  # REAL | DEMO | UNAVAILABLE


class Freshness(BaseModel):
    source: str
    retrieved_at: datetime
    observation_time: Optional[datetime] = None
    data_age_seconds: Optional[float] = None
    freshness_status: str
    provider_freshness_note: Optional[str] = None


class LocationFix(BaseModel):
    query: str
    name: str
    latitude: float
    longitude: float
    display_name: Optional[str] = None
    bbox: List[float]
    aoi_geojson: Dict[str, Any]
    radius_km: float
    source: str
    retrieved_at: datetime
    data_status: str


class SatelliteProduct(BaseModel):
    product_id: str
    title: str
    acquisition_time: Optional[str] = None
    platform: Optional[str] = None
    polarisation: Optional[str] = None
    product_type: Optional[str] = None
    processing_level: Optional[str] = None
    footprint: Optional[Dict[str, Any]] = None
    source_url: Optional[str] = None
    query_time: datetime
    data_freshness: Optional[Freshness] = None
    data_status: str = "REAL"


class SpillCandidate(BaseModel):
    candidate_id: str
    label: str  # OIL_SPILL_CANDIDATE | POTENTIAL_LOOKALIKE | DEMO_SYNTHETIC
    confirmed: bool = False
    geometry: Dict[str, Any]
    centroid_lat: float
    centroid_lon: float
    area_km2: float
    perimeter_km: Optional[float] = None
    orientation_deg: Optional[float] = None
    elongation: Optional[float] = None
    confidence: float
    method: str
    lookalike_warning: Optional[str] = None
    scene_id: Optional[str] = None
    acquisition_time: Optional[str] = None
    data_status: str
    provenance: str


class VesselRecord(BaseModel):
    mmsi: Optional[str] = None
    imo: Optional[str] = None
    name: Optional[str] = None
    vessel_type: str = "Unknown"
    flag: Optional[str] = None
    latitude: float
    longitude: float
    speed_knots: Optional[float] = None
    course_deg: Optional[float] = None
    heading_deg: Optional[float] = None
    destination: Optional[str] = None
    eta: Optional[str] = None
    ais_timestamp: Optional[str] = None
    distance_km: Optional[float] = None
    bearing_deg: Optional[float] = None
    provider: str
    data_status: str
    freshness: Optional[Freshness] = None
    track: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_score: Optional[float] = None
    evidence_class: Optional[str] = None


class InfrastructureRecord(BaseModel):
    feature_id: str
    name: Optional[str] = None
    kind: str  # pipeline | platform | port | terminal | unknown
    geometry: Dict[str, Any]
    operator: Optional[str] = None
    source: str
    dataset: str
    last_update: Optional[str] = None
    distance_km: Optional[float] = None
    data_status: str
    freshness: Optional[Freshness] = None
    notes: Optional[str] = None


class WeatherContext(BaseModel):
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wave_height_m: Optional[float] = None
    current_speed_ms: Optional[float] = None
    current_direction_deg: Optional[float] = None
    source: str
    observation_time: Optional[str] = None
    data_status: str
    freshness: Optional[Freshness] = None
    warning: Optional[str] = None


class Hypothesis(BaseModel):
    type: str
    confidence: float
    classification: str
    evidence: List[str] = Field(default_factory=list)


class AttributionResult(BaseModel):
    primary_hypothesis: str
    confidence: float
    classification: str
    alternatives: List[Hypothesis] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    method: str = "deterministic_spatial_temporal_scoring_v1"


class IntelligenceReport(BaseModel):
    success: bool = True
    mode: str
    location: Optional[LocationFix] = None
    satellite: Dict[str, Any] = Field(default_factory=dict)
    oil_spill_candidates: List[SpillCandidate] = Field(default_factory=list)
    vessels: List[VesselRecord] = Field(default_factory=list)
    vessel_tracks: List[Dict[str, Any]] = Field(default_factory=list)
    pipelines: List[InfrastructureRecord] = Field(default_factory=list)
    platforms: List[InfrastructureRecord] = Field(default_factory=list)
    ports: List[InfrastructureRecord] = Field(default_factory=list)
    weather: Optional[WeatherContext] = None
    source_attribution: Optional[AttributionResult] = None
    data_sources: List[str] = Field(default_factory=list)
    freshness: Dict[str, Any] = Field(default_factory=dict)
    provider_status: List[ProviderStatus] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    narrative: Optional[str] = None
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=utcnow)
