"""
Strongly Typed Data Contracts with Provenance Metadata

Every pipeline result carries data_status and source metadata for traceability.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DataStatus(str, Enum):
    REAL = "REAL"
    DEMO = "DEMO"
    SYNTHETIC = "SYNTHETIC"
    UNAVAILABLE = "UNAVAILABLE"


class ProvenanceMetadata(BaseModel):
    id: Optional[str] = None
    timestamp: datetime
    source: str
    model_version: Optional[str] = None
    confidence: Optional[float] = None
    uncertainty: Optional[float] = None
    data_status: DataStatus = DataStatus.REAL
    data_provenance: Optional[str] = None


class SceneMetadata(BaseModel):
    scene_id: Optional[str] = None
    scene_name: str
    acquisition_time: datetime
    source: str
    sensor_mode: str = "IW"
    polarization: List[str] = Field(default_factory=lambda: ["VV", "VH"])
    crs: Optional[str] = None
    transform: Optional[List[float]] = None
    bounds: Optional[List[float]] = None  # [min_lon, min_lat, max_lon, max_lat]
    bbox: List[float]
    resolution_m: Optional[float] = None
    storage_path: Optional[str] = None
    data_status: DataStatus = DataStatus.REAL


class SatelliteSceneContract(SceneMetadata):
    footprint_geojson: Dict[str, Any]
    is_synthetic: bool = False
    ingestion_status: str = "COMPLETED"


class SegmentationResult(BaseModel):
    class_mask_path: Optional[str] = None
    prob_maps_shape: Optional[List[int]] = None
    oil_probability_mean: Optional[float] = None
    lookalike_probability_mean: Optional[float] = None
    confidence_map_mean: Optional[float] = None
    model_version: str
    data_status: DataStatus
    preprocessing_version: str


class SpillGeometry(BaseModel):
    geom_geojson: Dict[str, Any]
    centroid_lat: float
    centroid_lon: float
    area_km2: float
    perimeter_km: float
    bbox: Optional[List[float]] = None
    crs: str = "EPSG:4326"
    area_method: str = "geodesic_wgs84_ellipsoid"


class ClassificationEvidence(BaseModel):
    segmentation_probability: float
    morphology_circularity: Optional[float] = None
    is_elongated_plume: Optional[bool] = None
    wind_regime: Optional[str] = None
    temporal_persistence: Optional[str] = None
    lookalike_risk_score: float = 0.0


class SpillDetectionContract(BaseModel):
    detection_id: Optional[str] = None
    observation_id: str
    geometry: SpillGeometry
    predicted_class: str
    classification_label: str  # e.g. "Potential Oil Slick", "Look-Alike Candidate"
    confidence: float
    uncertainty: float
    evidence: ClassificationEvidence
    model_version: str
    data_status: DataStatus
    timestamp: datetime


class EnvironmentalObservation(BaseModel):
    snapshot_id: Optional[str] = None
    variable: str
    source: str
    valid_time: datetime
    data_vintage: datetime
    bbox: List[float]
    u_component: Optional[float] = None
    v_component: Optional[float] = None
    magnitude: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_status: DataStatus = DataStatus.UNAVAILABLE


class TemporalObservationContract(BaseModel):
    id: Optional[str] = None
    track_id: str
    detection_id: str
    observation_time: datetime
    area_km2: float
    area_delta_km2: float = 0.0
    centroid_displacement_m: float = 0.0
    drift_speed_kmh: float = 0.0
    drift_heading_deg: float = 0.0
    growth_rate_km2_per_hr: float = 0.0
    observed_state: str
    data_status: DataStatus = DataStatus.REAL


class ForecastBandContract(BaseModel):
    horizon_hours: int
    target_time: datetime
    confidence_level: float
    geom_geojson: Dict[str, Any]
    area_km2: float
    centroid_lat: float
    centroid_lon: float
    mean_speed_kmh: float
    data_status: DataStatus = DataStatus.REAL


class ForecastContract(BaseModel):
    forecast_run_id: Optional[str] = None
    track_id: str
    run_time: datetime
    engine: str
    engine_version: str
    ensemble_size: int
    horizons_hours: List[int]
    bands: List[ForecastBandContract] = Field(default_factory=list)
    trajectory_points: List[Dict[str, Any]] = Field(default_factory=list)
    environmental_forcing: Dict[str, Any] = Field(default_factory=dict)
    data_status: DataStatus = DataStatus.REAL
    uncertainty_note: str = "Probabilistic forecast — not a guaranteed future position."


class ImpactAssessmentContract(BaseModel):
    id: Optional[str] = None
    forecast_run_id: str
    asset_id: str
    asset_name: str
    horizon_hours: int
    impact_probability: float
    earliest_time_to_impact_hours: float
    distance_to_slick_km: float
    intersected_area_km2: float = 0.0
    exposure_level: str
    impact_type: str = "PREDICTED_POTENTIAL"  # or OBSERVED
    data_status: DataStatus = DataStatus.REAL


class RiskFactorContribution(BaseModel):
    factor_name: str
    normalized_value: float
    weighted_points: float
    explanation: str


class RiskAssessmentContract(BaseModel):
    risk_id: Optional[str] = None
    total_risk_score: float
    risk_category: str
    risk_factors: List[RiskFactorContribution]
    explanation: str
    confidence: float
    data_status: DataStatus = DataStatus.REAL
    weight_config_version: str
