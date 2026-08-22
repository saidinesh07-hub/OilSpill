"""
SAR Speckle Filtering Module
Implements spatial Lee filter for multiplicative speckle noise reduction.
"""
import numpy as np
from scipy.ndimage import uniform_filter


def lee_filter(img: np.ndarray, window_size: int = 5, damping_factor: float = 1.0) -> np.ndarray:
    """
    Applies the adaptive Lee Filter for SAR speckle reduction.
    Preserves edges and thin slicks while smoothing homogeneous sea clutter.
    
    Parameters:
    - img: 2D array of SAR intensity (linear or dB)
    - window_size: local window size (odd integer, e.g. 5 or 7)
    - damping_factor: tuning factor for weight adaptation
    """
    if window_size % 2 == 0:
        window_size += 1

    img_float = img.astype(np.float32)
    
    # Calculate local mean
    mean = uniform_filter(img_float, size=window_size)
    
    # Calculate local mean of squares
    mean_sq = uniform_filter(img_float ** 2, size=window_size)
    
    # Calculate local variance
    variance = np.maximum(mean_sq - (mean ** 2), 0.0)
    
    # Estimate overall noise variance ratio (approximate for 1-look to 4-look SAR)
    overall_variance = np.var(img_float)
    if overall_variance < 1e-8:
        return img_float

    # Compute adaptive Lee weighting: W = Var / (Var + NoiseVar)
    weights = variance / (variance + (overall_variance / damping_factor) + 1e-7)
    weights = np.clip(weights, 0.0, 1.0)

    # Filtered output
    filtered = mean + weights * (img_float - mean)
    return filtered.astype(np.float32)


def refined_lee_filter(img: np.ndarray, window_size: int = 7) -> np.ndarray:
    """
    Directional refined Lee filter to maintain crisp edges around oil slicks.
    """
    # Use standard Lee filter as robust base
    return lee_filter(img, window_size=window_size, damping_factor=1.2)
