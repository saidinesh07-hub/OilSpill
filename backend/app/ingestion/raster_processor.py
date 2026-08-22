"""
SAR Raster Processor

Scientific preprocessing pipeline with documented assumptions.

Assumptions:
- Input may be raw DN, sigma0 linear, or sigma0 dB — detected via value range.
- Lee speckle filter applied only when input appears to be dB-scale SAR.
- Normalization maps dB to [0,1] for neural network input.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import numpy as np
from backend.app.ml.preprocessing.calibration import calibrate_sar_dn_to_sigma0, linear_to_db
from backend.app.ml.preprocessing.normalization import normalize_sar_db
from backend.app.ml.preprocessing.speckle import lee_filter
from backend.app.schemas.data_contract import DataStatus


@dataclass
class RasterProcessingResult:
    normalized: np.ndarray
    sar_db: np.ndarray
    metadata: Dict[str, Any]


class RasterProcessor:
    """Preprocesses SAR rasters for segmentation inference."""

    def detect_input_representation(self, raster: np.ndarray) -> str:
        """
        Infer whether raster is DN, linear sigma0, or dB sigma0.

        Heuristic based on value range — document uncertainty in metadata.
        """
        vmin, vmax = float(np.nanmin(raster)), float(np.nanmax(raster))
        if vmax <= 1.5 and vmin >= 0:
            return "linear_sigma0"
        if vmin >= -50 and vmax <= 20:
            return "db_sigma0"
        if vmax > 50:
            return "raw_dn"
        return "unknown"

    def process(
        self,
        raster: np.ndarray,
        nodata: Optional[float] = None,
        is_raw_dn: bool = False,
        data_status: DataStatus = DataStatus.REAL,
    ) -> RasterProcessingResult:
        rep = "raw_dn" if is_raw_dn else self.detect_input_representation(raster)
        working = raster.astype(np.float32)

        if nodata is not None:
            working = np.where(working == nodata, np.nan, working)
            fill = float(np.nanmean(working))
            working = np.nan_to_num(working, nan=fill)

        if rep == "raw_dn" or is_raw_dn:
            sar_db = calibrate_sar_dn_to_sigma0(working)
            assumption = "Converted raw DN to sigma0 dB via standard calibration"
        elif rep == "linear_sigma0":
            sar_db = linear_to_db(working)
            assumption = "Input treated as linear sigma0; converted to dB"
        elif rep == "db_sigma0":
            sar_db = working
            assumption = "Input already in sigma0 dB — no radiometric conversion applied"
        else:
            sar_db = working
            assumption = "Unknown input representation — passed through without calibration"

        despeckled = lee_filter(sar_db, window_size=5)
        normalized = normalize_sar_db(despeckled, min_db=-35.0, max_db=5.0)

        metadata = {
            "input_representation": rep,
            "assumption": assumption,
            "speckle_filter": "lee_window_5",
            "normalization_range_db": [-35.0, 5.0],
            "data_status": data_status.value,
        }
        return RasterProcessingResult(normalized=normalized, sar_db=despeckled, metadata=metadata)
