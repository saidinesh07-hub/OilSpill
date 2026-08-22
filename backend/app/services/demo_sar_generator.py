"""
Synthetic SAR Scene Generator — DEMO DATA ONLY

Generates representative Sentinel-1-like backscatter fields for pipeline testing.
Never use output from this module as real satellite observations.
"""
from typing import Dict, Tuple
import numpy as np


def generate_demo_sar_scene(
    height: int = 512,
    width: int = 512,
    pass_index: int = 0,
    seed: int = 42
) -> Tuple[np.ndarray, Dict]:
    """
    Create a labeled synthetic SAR sigma0 (dB) raster with an injected dark slick.

    pass_index shifts slick centroid between multi-pass demo sequences.
    """
    rng = np.random.default_rng(seed + pass_index)
    sar = rng.normal(-22.0, 2.5, size=(height, width)).astype(np.float32)

    cy = int(height * (0.45 + 0.02 * pass_index))
    cx = int(width * (0.52 + 0.01 * pass_index))
    yy, xx = np.ogrid[:height, :width]
    slick_mask = (((xx - cx) ** 2) / (55 ** 2) + ((yy - cy) ** 2) / (28 ** 2)) <= 1.0
    sar[slick_mask] = rng.normal(-32.0, 1.2, size=int(np.sum(slick_mask)))

    metadata = {
        "data_mode": "DEMO_DATA",
        "data_provenance": "SYNTHETIC — not from Copernicus or any satellite",
        "generator": "demo_sar_generator.generate_demo_sar_scene",
        "pass_index": pass_index,
        "slick_pixel_count": int(np.sum(slick_mask)),
    }
    return sar, metadata
