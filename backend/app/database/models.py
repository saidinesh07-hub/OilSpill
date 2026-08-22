"""
Database Models Specification
Implements the immutable state ledger and spatial entities.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Text, JSON, Boolean, Index
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base


def generate_uuid():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    model_name = Column(String, nullable=False)  # e.g., "deeplabv3plus_resnet50"
    version_tag = Column(String, nullable=False, unique=True)
    task = Column(String, nullable=False)  # "segmentation", "lookalike", "forecasting_correction"
    weights_path = Column(String, nullable=True)
    metrics = Column(JSON, nullable=True)  # e.g., {"mIoU": 0.742, "oil_iou": 0.685}
    dataset_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class SatelliteScene(Base):
    """Raw or cataloged SAR satellite scenes (e.g. Sentinel-1)."""
    __tablename__ = "satellite_scenes"

    scene_id = Column(String, primary_key=True, default=generate_uuid)
    scene_name = Column(String, nullable=False, index=True)
    source = Column(String, default="Sentinel-1 SAR")  # Sentinel-1A, Sentinel-1C, etc.
    sensor_mode = Column(String, default="IW")  # IW, EW, SM
    polarization = Column(JSON, default=lambda: ["VV", "VH"])
    acquisition_time = Column(DateTime, nullable=False, index=True)
    footprint_geojson = Column(JSON, nullable=False)  # WGS84 GeoJSON Polygon
    bbox = Column(JSON, nullable=False)  # [min_lon, min_lat, max_lon, max_lat]
    incidence_angle_min = Column(Float, nullable=True)
    incidence_angle_max = Column(Float, nullable=True)
    storage_path = Column(String, nullable=True)
    is_synthetic = Column(Boolean, default=False)
    ingestion_status = Column(String, default="COMPLETED")  # PENDING, PROCESSING, COMPLETED, FAILED
    created_at = Column(DateTime, default=utc_now)

    observations = relationship("Observation", back_populates="scene", cascade="all, delete-orphan")


class Observation(Base):
    """Preprocessed raster tiles and spatial grids derived from a scene."""
    __tablename__ = "observations"

    observation_id = Column(String, primary_key=True, default=generate_uuid)
    scene_id = Column(String, ForeignKey("satellite_scenes.scene_id"), nullable=False, index=True)
    preprocessing_version = Column(String, default="v1.0-lee-filter-sigma0")
    tile_grid_id = Column(String, nullable=True)
    processed_at = Column(DateTime, default=utc_now)
    raster_metadata = Column(JSON, default=dict)
    
    scene = relationship("SatelliteScene", back_populates="observations")
    detections = relationship("SpillDetection", back_populates="observation", cascade="all, delete-orphan")


class SpillDetection(Base):
    """A detected polygon within an observation with confidence and classification."""
    __tablename__ = "spill_detections"

    detection_id = Column(String, primary_key=True, default=generate_uuid)
    observation_id = Column(String, ForeignKey("observations.observation_id"), nullable=False, index=True)
    geom_geojson = Column(JSON, nullable=False)  # GeoJSON Polygon/MultiPolygon in EPSG:4326
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    area_km2 = Column(Float, nullable=False)  # Exact geodetic area in sq km
    perimeter_km = Column(Float, nullable=False)
    predicted_class = Column(String, nullable=False)  # "oil_spill", "look_alike", "ship", "land", "sea_surface"
    confidence = Column(Float, nullable=False)  # Calibrated probability [0.0 - 1.0]
    lookalike_risk_score = Column(Float, default=0.0)  # Specific lookalike confusion index
    morphology_features = Column(JSON, default=dict)  # Aspect ratio, circularity, texture variance
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    observation = relationship("Observation", back_populates="detections")
    temporal_observations = relationship("TemporalObservation", back_populates="detection")


class TrackedSlick(Base):
    """Unique physical slick entity tracked across multiple satellite scenes through time."""
    __tablename__ = "tracked_slicks"

    track_id = Column(String, primary_key=True, default=generate_uuid)
    slick_name = Column(String, nullable=False, index=True)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    current_status = Column(String, default="ACTIVE")  # ACTIVE, DISSIPATED, BEACHED, UNKNOWN
    total_area_km2 = Column(Float, default=0.0)
    current_centroid_lat = Column(Float, nullable=True)
    current_centroid_lon = Column(Float, nullable=True)
    drift_speed_kmh = Column(Float, default=0.0)
    drift_heading_deg = Column(Float, default=0.0)
    growth_rate_km2_per_hr = Column(Float, default=0.0)
    latest_detection_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    temporal_observations = relationship("TemporalObservation", back_populates="track", cascade="all, delete-orphan")
    forecast_runs = relationship("ForecastRun", back_populates="track", cascade="all, delete-orphan")


class TemporalObservation(Base):
    """Association node linking a specific detection at time T to a tracked slick entity."""
    __tablename__ = "temporal_observations"

    id = Column(String, primary_key=True, default=generate_uuid)
    track_id = Column(String, ForeignKey("tracked_slicks.track_id"), nullable=False, index=True)
    detection_id = Column(String, ForeignKey("spill_detections.detection_id"), nullable=False, index=True)
    observation_time = Column(DateTime, nullable=False, index=True)
    area_km2 = Column(Float, nullable=False)
    area_delta_km2 = Column(Float, default=0.0)
    centroid_displacement_m = Column(Float, default=0.0)
    observed_state = Column(String, nullable=False)  # "EXPANSION", "CONTRACTION", "FRAGMENTATION", "PERSISTENCE", "DISAPPEARANCE"
    advection_iou_match = Column(Float, default=1.0)
    notes = Column(Text, nullable=True)

    track = relationship("TrackedSlick", back_populates="temporal_observations")
    detection = relationship("SpillDetection", back_populates="temporal_observations")


class EnvironmentalSnapshot(Base):
    """Cached oceanographic & meteorological forcing variables (currents, winds, waves)."""
    __tablename__ = "environmental_snapshots"

    snapshot_id = Column(String, primary_key=True, default=generate_uuid)
    variable = Column(String, nullable=False)  # "ocean_currents_uv", "surface_wind_uv", "waves_stokes_drift"
    source = Column(String, nullable=False)  # "CMEMS_PHYSICS", "ECMWF_ERA5", "NOAA_GFS"
    valid_time = Column(DateTime, nullable=False, index=True)
    data_vintage = Column(DateTime, nullable=False)  # Time the forecast/reanalysis was issued
    bbox = Column(JSON, nullable=False)
    u_mean = Column(Float, default=0.0)
    v_mean = Column(Float, default=0.0)
    magnitude_mean = Column(Float, default=0.0)
    grid_data = Column(JSON, nullable=True)  # Lightweight localized vector grid for client display
    storage_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class ForecastRun(Base):
    """A simulation run of slick trajectory advection and uncertainty dispersion."""
    __tablename__ = "forecast_runs"

    forecast_run_id = Column(String, primary_key=True, default=generate_uuid)
    track_id = Column(String, ForeignKey("tracked_slicks.track_id"), nullable=False, index=True)
    run_time = Column(DateTime, default=utc_now, index=True)
    engine = Column(String, default="Lagrangian_Advection_Ensemble")  # "Lagrangian_Advection_Ensemble", "OpenDrift", "PyGNOME"
    engine_version = Column(String, default="v1.2.0-metocean-stokes")
    ensemble_size = Column(Integer, default=50)
    forcing_snapshot_ids = Column(JSON, default=list)
    wind_drift_factor = Column(Float, default=0.03)  # 3% wind leeway rule
    wind_deflection_angle_deg = Column(Float, default=15.0)  # Coriolis deflection
    diffusion_coefficient = Column(Float, default=2.0)  # m2/s
    confidence_decay_rate = Column(Float, default=0.008)  # per hour
    summary = Column(JSON, default=dict)

    track = relationship("TrackedSlick", back_populates="forecast_runs")
    bands = relationship("ForecastBand", back_populates="forecast_run", cascade="all, delete-orphan")
    impacts = relationship("ImpactAssessment", back_populates="forecast_run", cascade="all, delete-orphan")


class ForecastBand(Base):
    """Spatiotemporal confidence containment contours for a forecast lead time."""
    __tablename__ = "forecast_bands"

    id = Column(String, primary_key=True, default=generate_uuid)
    forecast_run_id = Column(String, ForeignKey("forecast_runs.forecast_run_id"), nullable=False, index=True)
    horizon_hours = Column(Integer, nullable=False, index=True)  # 6, 12, 24, 48
    target_time = Column(DateTime, nullable=False)
    confidence_level = Column(Float, nullable=False)  # 0.50 (best guess), 0.80 (standard), 0.95 (conservative/minimum regret)
    geom_geojson = Column(JSON, nullable=False)  # Polygon of uncertainty envelope
    area_km2 = Column(Float, nullable=False)
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    mean_speed_kmh = Column(Float, default=0.0)

    forecast_run = relationship("ForecastRun", back_populates="bands")


class Asset(Base):
    """Static and semi-static environmental, ecological, and socio-economic assets."""
    __tablename__ = "assets"

    asset_id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    asset_type = Column(String, nullable=False, index=True)  # "protected_area", "fishery", "port", "beach", "wetland", "coastal_population"
    geom_geojson = Column(JSON, nullable=False)  # Point/Polygon GeoJSON
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    sensitivity_weight = Column(Float, default=1.0)  # 1.0 (standard) to 5.0 (critical coral reef / MPA)
    data_source = Column(String, default="WDPA / OSM / GFW")
    data_vintage = Column(DateTime, default=utc_now)
    properties = Column(JSON, default=dict)  # Description, IUCN category, economic value

    impacts = relationship("ImpactAssessment", back_populates="asset")


class ImpactAssessment(Base):
    """Spatiotemporal intersection between forecast trajectory envelope and assets."""
    __tablename__ = "impact_assessments"

    id = Column(String, primary_key=True, default=generate_uuid)
    forecast_run_id = Column(String, ForeignKey("forecast_runs.forecast_run_id"), nullable=False, index=True)
    asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False, index=True)
    horizon_hours = Column(Integer, nullable=False)
    impact_probability = Column(Float, nullable=False)  # [0.0 - 1.0] based on confidence band intersection
    earliest_time_to_impact_hours = Column(Float, nullable=False)
    distance_to_slick_km = Column(Float, nullable=False)
    intersected_area_km2 = Column(Float, default=0.0)
    exposure_level = Column(String, nullable=False)  # "CRITICAL", "HIGH", "MODERATE", "LOW", "NEGLIGIBLE"
    created_at = Column(DateTime, default=utc_now)

    forecast_run = relationship("ForecastRun", back_populates="impacts")
    asset = relationship("Asset", back_populates="impacts")
    risk_assessment = relationship("RiskAssessment", back_populates="impact", uselist=False, cascade="all, delete-orphan")


class RiskAssessment(Base):
    """Decomposed, fully explainable risk evaluation for an impacted asset."""
    __tablename__ = "risk_assessments"

    risk_id = Column(String, primary_key=True, default=generate_uuid)
    impact_assessment_id = Column(String, ForeignKey("impact_assessments.id"), nullable=False, unique=True, index=True)
    total_risk_score = Column(Float, nullable=False)  # [0.0 - 100.0]
    risk_category = Column(String, nullable=False)  # "VERY_HIGH", "HIGH", "MODERATE", "LOW"
    
    # 6 Decomposed contributing factor scores [0.0 - 1.0 normalized]:
    factor_impact_probability = Column(Float, nullable=False)
    factor_asset_sensitivity = Column(Float, nullable=False)
    factor_proximity = Column(Float, nullable=False)
    factor_slick_expansion = Column(Float, nullable=False)
    factor_forecast_uncertainty = Column(Float, nullable=False)
    factor_economic_exposure = Column(Float, nullable=False)

    factor_breakdown = Column(JSON, nullable=False)
    explanation_text = Column(Text, nullable=False)
    weight_config_version = Column(String, default="v1.0-AHP-standard")
    calculated_at = Column(DateTime, default=utc_now)

    impact = relationship("ImpactAssessment", back_populates="risk_assessment")
    recommendations = relationship("ResponseRecommendation", back_populates="risk_assessment", cascade="all, delete-orphan")


class ResponseRecommendation(Base):
    """Decision-support guidance, response priority, and monitoring task recommendations."""
    __tablename__ = "response_recommendations"

    id = Column(String, primary_key=True, default=generate_uuid)
    risk_id = Column(String, ForeignKey("risk_assessments.risk_id"), nullable=False, index=True)
    priority_rank = Column(Integer, nullable=False)  # 1, 2, 3...
    action_category = Column(String, nullable=False)  # "CONTAINMENT_DEPLOYMENT", "AERIAL_VERIFICATION", "SATELLITE_RETASKING", "SHORELINE_DEFENSE"
    recommendation_text = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    time_window_hours = Column(Float, nullable=False)
    target_geom_geojson = Column(JSON, nullable=True)
    analyst_review_status = Column(String, default="PENDING_REVIEW")  # "PENDING_REVIEW", "VALIDATED", "DISMISSED"
    created_at = Column(DateTime, default=utc_now)

    risk_assessment = relationship("RiskAssessment", back_populates="recommendations")


class AnalysisSession(Base):
    """Auditable session tracking user interactions, queries, and active tracks."""
    __tablename__ = "analysis_sessions"

    session_id = Column(String, primary_key=True, default=generate_uuid)
    session_title = Column(String, default="Operational Incident Analysis")
    started_at = Column(DateTime, default=utc_now)
    active_track_ids = Column(JSON, default=list)
    assistant_query_count = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
