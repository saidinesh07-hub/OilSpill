"""
SAR Backscatter Normalization Module
Scales calibrated SAR dB data into standardized neural network input ranges.
"""
import numpy as np
from backend.app.ml.constants import SAR_SIGMA0_MIN_DB, SAR_SIGMA0_MAX_DB


def normalize_sar_db(
    sar_db: np.ndarray,
    min_db: float = SAR_SIGMA0_MIN_DB,
    max_db: float = SAR_SIGMA0_MAX_DB,
    target_range: str = "zero_one"  # "zero_one" [0, 1] or "unit" [-1, 1]
) -> np.ndarray:
    """
    Clips and normalizes SAR backscatter in dB to standard neural network range.
    """
    clipped = np.clip(sar_db, min_db, max_db)
    norm = (clipped - min_db) / (max_db - min_db + 1e-7)
    
    if target_range == "unit":
        return (norm * 2.0 - 1.0).astype(np.float32)
    return norm.astype(np.float32)


def standardize_sar(sar_array: np.ndarray, mean: float = -18.0, std: float = 6.5) -> np.ndarray:
    """Z-score standardization based on global SAR ocean backscatter statistics."""
    return ((sar_array - mean) / (std + 1e-7)).astype(np.float32)
