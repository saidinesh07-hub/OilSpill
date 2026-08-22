"""
Satellite Scene Ingestion Service
Handles Sentinel-1 SAFE product metadata parsing, footprint geometry extraction, and registration.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from shapely.geometry import Polygon, mapping
from sqlalchemy.orm import Session
from backend.app.core.logging import logger
from backend.app.database.models import SatelliteScene
from backend.app.services.cdse_client import CDSEClient


class SceneIngestionService:
    """
    Ingestion service for Copernicus Sentinel-1 SAR scenes.
    """
    def __init__(self, db: Session):
        self.db = db

    def register_scene(
        self,
        scene_name: str,
        acquisition_time: datetime,
        bbox: List[float],  # [min_lon, min_lat, max_lon, max_lat]
        source: str = "Sentinel-1A SAR IW",
        sensor_mode: str = "IW",
        polarization: Optional[List[str]] = None,
        incidence_angle_min: float = 30.5,
        incidence_angle_max: float = 45.2,
        is_synthetic: bool = False,
        storage_path: Optional[str] = None
    ) -> SatelliteScene:
        """
        Creates and stores satellite scene record with WGS84 footprint geometry.
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        footprint_poly = Polygon([
            (min_lon, min_lat),
            (max_lon, min_lat),
            (max_lon, max_lat),
            (min_lon, max_lat),
            (min_lon, min_lat)
        ])

        scene = SatelliteScene(
            scene_name=scene_name,
            source=source,
            sensor_mode=sensor_mode,
            polarization=polarization or ["VV", "VH"],
            acquisition_time=acquisition_time,
            footprint_geojson=mapping(footprint_poly),
            bbox=bbox,
            incidence_angle_min=incidence_angle_min,
            incidence_angle_max=incidence_angle_max,
            is_synthetic=is_synthetic,
            storage_path=storage_path,
            ingestion_status="COMPLETED"
        )

        self.db.add(scene)
        self.db.commit()
        self.db.refresh(scene)
        logger.info(f"Registered satellite scene '{scene_name}' (ID: {scene.scene_id})")
        return scene

    def search_cdse_sentinel1(
        self,
        bbox: List[float],
        start: datetime,
        end: datetime,
        product_type: str = "GRD",
    ) -> Dict[str, Any]:
        """Search Copernicus Data Space for Sentinel-1 products (requires CDSE credentials)."""
        client = CDSEClient()
        return client.search_sentinel1(bbox=bbox, start=start, end=end, product_type=product_type)

    def ingest_from_local_geotiff(
        self,
        scene_name: str,
        acquisition_time: datetime,
        geotiff_path: str,
        source: str = "Sentinel-1 SAR IW",
        is_synthetic: bool = False,
    ) -> SatelliteScene:
        """
        Register a scene from a local georeferenced SAR GeoTIFF (real data path).
        """
        from backend.app.geospatial.sar_reader import read_sar_geotiff, validate_geospatial_metadata

        _, metadata = read_sar_geotiff(geotiff_path)
        if not validate_geospatial_metadata(metadata):
            raise ValueError("GeoTIFF missing CRS or geotransform — cannot register scene.")

        bounds = metadata["bounds"]
        bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]

        return self.register_scene(
            scene_name=scene_name,
            acquisition_time=acquisition_time,
            bbox=bbox,
            source=source,
            is_synthetic=is_synthetic,
            storage_path=geotiff_path,
        )
