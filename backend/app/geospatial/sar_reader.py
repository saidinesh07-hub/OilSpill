"""
SAR Raster Reader

Reads georeferenced Sentinel-1 SAR rasters via rasterio, preserving CRS and affine transform.
"""
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np
from backend.app.core.logging import logger

try:
    import rasterio
    from rasterio.windows import Window
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False


def read_sar_geotiff(
    path: str,
    band_index: int = 1,
    window: Optional[Tuple[int, int, int, int]] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Read a SAR GeoTIFF band and return array plus geospatial metadata.

    window: optional (col_off, row_off, width, height) for tiled reads.
    """
    if not HAS_RASTERIO:
        raise ImportError(
            "rasterio is required for SAR GeoTIFF ingestion. "
            "Install with: pip install rasterio"
        )

    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"SAR raster not found: {path}")

    with rasterio.open(path) as src:
        read_window = None
        if window:
            read_window = Window(window[0], window[1], window[2], window[3])

        data = src.read(band_index, window=read_window)
        if data.ndim == 3:
            data = data[0]

        transform = src.window_transform(read_window) if read_window else src.transform

        metadata = {
            "data_mode": "REAL_SATELLITE_DATA",
            "source_path": str(path_obj.resolve()),
            "crs": src.crs.to_string() if src.crs else None,
            "transform": list(transform)[:6],
            "width": data.shape[1],
            "height": data.shape[0],
            "dtype": str(data.dtype),
            "bounds": src.bounds if not read_window else rasterio.windows.bounds(read_window, src.transform),
            "acquisition_time": src.tags().get("ACQUISITION_TIME"),
        }

    logger.info(f"Read SAR raster {path} shape={data.shape} CRS={metadata['crs']}")
    return data.astype(np.float32), metadata


def validate_geospatial_metadata(metadata: Dict[str, Any]) -> bool:
    """Ensure CRS and transform are present before geospatial reconstruction."""
    return bool(metadata.get("crs")) and bool(metadata.get("transform"))
