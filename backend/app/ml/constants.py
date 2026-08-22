"""
ML and Remote Sensing Constants
Implements the 5-class Krestenitis SAR oil-spill benchmark schema.
"""
from typing import Dict, List

# 5-Class Segmentation Schema
CLASS_NAMES: List[str] = [
    "sea_surface",  # 0
    "oil_spill",    # 1
    "look_alike",   # 2
    "ship",         # 3
    "land"          # 4
]

CLASS_ID_TO_NAME: Dict[int, str] = {i: name for i, name in enumerate(CLASS_NAMES)}
CLASS_NAME_TO_ID: Dict[str, int] = {name: i for i, name in enumerate(CLASS_NAMES)}

# Visual Palette for Map and Diagnostics (Hex colors)
CLASS_COLORS_HEX: Dict[str, str] = {
    "sea_surface": "#0f172a",  # Deep navy slate
    "oil_spill": "#ef4444",    # Vivid red / danger
    "look_alike": "#f59e0b",   # Amber / warning (moderate uncertainty)
    "ship": "#06b6d4",         # Cyan / point target
    "land": "#22c55e"          # Emerald green / terrain
}

CLASS_COLORS_RGB: Dict[int, tuple] = {
    0: (15, 23, 42),     # sea
    1: (239, 68, 68),    # oil
    2: (245, 158, 11),   # look-alike
    3: (6, 182, 212),    # ship
    4: (34, 197, 94)     # land
}

# Loss weights to handle severe SAR class imbalance (sea surface is 90%+ of pixels)
DEFAULT_CLASS_WEIGHTS: List[float] = [
    0.2,   # sea_surface (heavily downweighted)
    3.0,   # oil_spill (high priority)
    2.5,   # look_alike (high priority for discrimination)
    2.0,   # ship
    1.0    # land
]

# Standard Sentinel-1 IW SAR processing constants
SENTINEL1_DEFAULT_PIXEL_SPACING_M = 10.0  # 10m GRD pixel spacing
SAR_SIGMA0_MIN_DB = -35.0  # Deep ocean backscatter floor in dB
SAR_SIGMA0_MAX_DB = 5.0    # Land / bright target backscatter ceiling in dB
