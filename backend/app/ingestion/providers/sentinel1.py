"""
Sentinel-1 SAR Data Provider

Supports:
- Local GeoTIFF/COG ingestion (REAL path)
- CDSE catalogue search (requires credentials)
- Demo synthetic raster generation (DEMO path)
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ingestion.providers.base import SatelliteDataProvider
from backend.app.schemas.data_contract import DataStatus, SceneMetadata
from backend.app.services.cdse_client import CDSEClient
from backend.app.services.demo_sar_generator import generate_demo_sar_scene


class Sentinel1Provider(SatelliteDataProvider):
    """Sentinel-1 IW GRD provider with local-file and demo fallback."""

    def __init__(self, data_mode: Optional[str] = None):
        self.data_mode = (data_mode or settings.DATA_MODE).upper()
        self.cdse = CDSEClient()

    def get_data_status(self) -> DataStatus:
        if self.data_mode == "REAL":
            return DataStatus.REAL
        return DataStatus.DEMO

    def search_scenes(
        self,
        bbox: List[float],
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        return self.cdse.search_sentinel1(bbox=bbox, start=start, end=end)

    def load_scene_raster(
        self,
        scene_ref: str,
        band_index: int = 1,
        pass_index: int = 0,
    ) -> tuple[np.ndarray, SceneMetadata]:
        """
        Load SAR raster from local GeoTIFF path or generate demo data.

        scene_ref: filesystem path to GeoTIFF, or 'demo' for synthetic scene.
        """
        if scene_ref.lower() in ("demo", "synthetic") or self.data_mode == "DEMO":
            if Path(scene_ref).exists() and scene_ref.lower() not in ("demo", "synthetic"):
                return self._load_geotiff(scene_ref, band_index, DataStatus.REAL)

            sar, demo_meta = generate_demo_sar_scene(pass_index=pass_index)
            meta = SceneMetadata(
                scene_name=f"DEMO_SAR_{pass_index}",
                acquisition_time=datetime.now(),
                source="DEMO synthetic SAR generator",
                bbox=[80.25, 13.15, 80.45, 13.35],
                data_status=DataStatus.DEMO,
                data_provenance=demo_meta.get("data_provenance"),
            )
            return sar, meta

        path = Path(scene_ref)
        if not path.exists():
            raise FileNotFoundError(
                f"Sentinel-1 raster not found: {scene_ref}. "
                "Place a GeoTIFF in data/raw_scenes/ or set DATA_MODE=DEMO."
            )
        return self._load_geotiff(str(path), band_index, DataStatus.REAL)

    def _load_geotiff(
        self,
        path: str,
        band_index: int,
        data_status: DataStatus,
    ) -> tuple[np.ndarray, SceneMetadata]:
        from backend.app.geospatial.sar_reader import read_sar_geotiff

        raster, reader_meta = read_sar_geotiff(path, band_index=band_index)
        bounds = reader_meta["bounds"]
        bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]

        meta = SceneMetadata(
            scene_name=Path(path).stem,
            acquisition_time=datetime.now(),
            source=f"Local GeoTIFF: {path}",
            crs=reader_meta.get("crs"),
            transform=reader_meta.get("transform"),
            bounds=bbox,
            bbox=bbox,
            storage_path=path,
            data_status=data_status,
            data_provenance="Ingested from local Sentinel-1-compatible GeoTIFF",
        )
        logger.info(f"Loaded REAL SAR raster from {path} shape={raster.shape}")
        return raster, meta

    def discover_local_scenes(self, directory: str = "data/raw_scenes") -> List[str]:
        """List GeoTIFF files available for REAL mode ingestion."""
        root = Path(directory)
        if not root.exists():
            return []
        extensions = ("*.tif", "*.tiff", "*.TIF", "*.TIFF")
        files: List[str] = []
        for ext in extensions:
            files.extend(str(p) for p in root.glob(ext))
        return sorted(files)
