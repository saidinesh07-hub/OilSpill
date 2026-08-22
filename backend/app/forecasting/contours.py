"""
Uncertainty Envelope and Containment Contour Generator
Constructs 50%, 80%, and 95% probability contours from particle ensemble distributions.
"""
from typing import Any, Dict, List, Tuple
import numpy as np
from shapely.geometry import MultiPoint, Polygon, mapping
from backend.app.geospatial.geometry_ops import compute_geodetic_area_km2, repair_and_clean_geometry


def compute_containment_contours_for_particles(
    particle_lons: np.ndarray,
    particle_lats: np.ndarray,
    confidence_levels: List[float] = [0.50, 0.80, 0.95]
) -> List[Dict[str, Any]]:
    """
    Computes quantile-bounded uncertainty polygons representing 50%, 80%, and 95% containment fields.
    """
    assert len(particle_lons) == len(particle_lats)
    n = len(particle_lons)
    if n < 3:
        return []

    c_lon = float(np.mean(particle_lons))
    c_lat = float(np.mean(particle_lats))

    # Calculate distance of each particle from centroid
    dists = np.sqrt((particle_lons - c_lon) ** 2 + (particle_lats - c_lat) ** 2)

    results = []
    sorted_indices = np.argsort(dists)

    for conf in sorted(confidence_levels):
        # Subset particles up to quantile
        k = max(4, int(np.ceil(conf * n)))
        subset_idx = sorted_indices[:k]
        sub_lons = particle_lons[subset_idx]
        sub_lats = particle_lats[subset_idx]

        points = [(float(lo), float(la)) for lo, la in zip(sub_lons, sub_lats)]
        mp = MultiPoint(points)
        
        # Buffer slightly based on confidence level to account for spatial diffusion
        buffer_deg = 0.003 * (1.0 + (conf - 0.5))
        poly = mp.convex_hull.buffer(buffer_deg)

        if isinstance(poly, Polygon) and not poly.is_empty and poly.is_valid:
            poly = repair_and_clean_geometry(poly)
            area_km2 = compute_geodetic_area_km2(poly)
            cent = poly.centroid

            results.append({
                "confidence_level": conf,
                "geom_geojson": mapping(poly),
                "area_km2": area_km2,
                "centroid_lon": round(cent.x, 7),
                "centroid_lat": round(cent.y, 7)
            })

    return results
