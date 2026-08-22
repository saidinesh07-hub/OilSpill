"""
SAR Radiometric Calibration Module
Converts raw Digital Numbers (DN) to calibrated radar backscatter sigma0 (dB).
"""
import numpy as np


def calibrate_sar_dn_to_sigma0(
    dn_array: np.ndarray,
    calibration_vector: float = 1.0,
    noise_floor: float = 1e-5
) -> np.ndarray:
    """
    Converts raw amplitude Digital Numbers (DN) to radar backscatter coefficient sigma0 (dB).
    Formula: sigma0_linear = (DN^2) / A_sigma^2
             sigma0_dB = 10 * log10(sigma0_linear)
    """
    dn_clean = np.maximum(dn_array.astype(np.float32), noise_floor)
    sigma0_linear = (dn_clean ** 2) / (calibration_vector ** 2)
    sigma0_linear = np.maximum(sigma0_linear, noise_floor)
    sigma0_db = 10.0 * np.log10(sigma0_linear)
    return sigma0_db


def linear_to_db(linear_array: np.ndarray, min_val: float = 1e-7) -> np.ndarray:
    """Safely converts linear SAR power intensity to dB scale."""
    clipped = np.maximum(linear_array, min_val)
    return 10.0 * np.log10(clipped)


def db_to_linear(db_array: np.ndarray) -> np.ndarray:
    """Converts dB backscatter to linear power intensity."""
    return 10.0 ** (db_array / 10.0)
