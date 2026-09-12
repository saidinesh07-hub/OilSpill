"""
Application Configuration Module
Centralized settings management using Pydantic Settings.
"""
from typing import List, Optional, Union
import json
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Oil Spill Intelligence System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    DATA_MODE: str = "DEMO"  # DEMO or REAL

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    # Database
    DATABASE_URL: str = "sqlite:///./data/oil_spill_intelligence.db"

    # Satellite Ingestion (Copernicus Data Space Ecosystem)
    CDSE_CLIENT_ID: Optional[str] = None
    CDSE_CLIENT_SECRET: Optional[str] = None
    CDSE_USERNAME: Optional[str] = None
    CDSE_PASSWORD: Optional[str] = None
    CDSE_API_URL: str = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

    # Oceanographic Data (Copernicus Marine Service - CMEMS)
    CMEMS_USERNAME: Optional[str] = None
    CMEMS_PASSWORD: Optional[str] = None

    # Meteorological Data (ECMWF CDS / NOAA GFS)
    CDS_API_KEY: Optional[str] = None
    CDS_API_URL: str = "https://cds.climate.copernicus.eu/api/v2"

    # External Asset Layers
    WDPA_API_KEY: Optional[str] = None
    GLOBAL_FISHING_WATCH_API_KEY: Optional[str] = None

    # Optional AIS / vessel providers (REAL mode never invents positions)
    AIS_API_KEY: Optional[str] = None
    AIS_API_URL: Optional[str] = None
    AISHUB_USERNAME: Optional[str] = None
    NOMINATIM_USER_AGENT: str = "OilSpillIntelligenceSystem/1.0 (research; contact=local)"
    
    # OSIRIS Maritime Intelligence Integration
    OSIRIS_ENABLED: bool = True
    OSIRIS_BASE_URL: str = "https://osirisai.live"
    OSIRIS_TIMEOUT_SECONDS: int = 10

    # AI Assistant
    LLM_PROVIDER: str = "local_heuristic"  # Options: "local_heuristic", "openai", "gemini"
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # ML & Computation
    DEVICE: str = "cpu"
    MODEL_CHECKPOINT_DIR: str = "./ml/experiments/checkpoints"
    DEFAULT_SEGMENTATION_MODEL: str = "deeplabv3plus"
    BATCH_SIZE: int = 8
    TILE_SIZE: int = 256
    TILE_OVERLAP: int = 32

    # Trajectory Forecasting
    DEFAULT_ENSEMBLE_SIZE: int = 50
    FORECAST_HORIZONS_HOURS: Union[List[int], str] = [6, 12, 24, 48]

    @field_validator("FORECAST_HORIZONS_HOURS", mode="before")
    @classmethod
    def parse_horizons(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [int(x.strip()) for x in v.strip("[]").split(",") if x.strip()]
        return v


settings = Settings()
