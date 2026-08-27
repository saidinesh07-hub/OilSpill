"""Practical SAR dark-spot oil-slick candidate detector. Not a confirmed oil classification."""
from typing import Any, Dict, List, Optional
import numpy as np
from scipy.ndimage import binary_opening, binary_closing, label, generate_binary_structure
from shapely.geometry import MultiPoint, mapping, Polygon
from backend.app.geospatial.geometry_ops import (
    compute_geodetic_area_km2,
    compute_geodetic_perimeter_km,
    repair_and_clean_geometry,
)


def _pixel_to_lonlat(row: float, col: float, bbox: List[float], height: int, width: int):
    min_lon, min_lat, max_lon, max_lat = bbox
    lon = min_lon + (col / max(width - 1, 1)) * (max_lon - min_lon)
    lat = max_lat - (row / max(height - 1, 1)) * (max_lat - min_lat)
    return lon, lat


def detect_dark_spot_candidates(
    vv: np.ndarray,
    bbox: List[float],
    mask: Optional[np.ndarray] = None,
    vh: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Detect locally dark SAR patches over water-like pixels.
    Returns OIL SLICK CANDIDATES only — never confirmed oil.
    """
    if vv is None or vv.size == 0:
        return {
            "status": "UNAVAILABLE",
            "message": "No SAR pixel array available for detection.",
            "candidates": [],
        }

    arr = np.array(vv, dtype=np.float32)
    valid = np.isfinite(arr)
    if mask is not None:
        valid &= np.array(mask) > 0.5
    if np.sum(valid) < 200:
        return {
            "status": "NO_CANDIDATE",
            "message": "Too few valid SAR pixels in this window.",
            "candidates": [],
        }

    water = valid & (arr < np.nanpercentile(arr[valid], 70))
    if np.sum(water) < 100:
        water = valid

    sea = arr[water]
    p15 = float(np.nanpercentile(sea, 15))
    p40 = float(np.nanpercentile(sea, 40))
    dark = valid & (arr <= p15) & (arr < (p40 - 1.5))
    if vh is not None:
        vh_arr = np.array(vh, dtype=np.float32)
        vh_ok = np.isfinite(vh_arr)
        dark &= (~vh_ok) | (vh_arr < np.nanpercentile(vh_arr[vh_ok & valid], 30))

    struct = generate_binary_structure(2, 2)
    dark = binary_opening(dark, structure=struct, iterations=1)
    dark = binary_closing(dark, structure=struct, iterations=2)

    labeled, nfeat = label(dark)
    h, w = arr.shape
    candidates: List[Dict[str, Any]] = []
    min_pixels = max(25, int(0.0004 * h * w))

    for fid in range(1, nfeat + 1):
        comp = labeled == fid
        pix = int(np.sum(comp))
        if pix < min_pixels:
            continue
        rows, cols = np.where(comp)
        step = max(1, len(rows) // 80)
        pts = [_pixel_to_lonlat(rows[i], cols[i], bbox, h, w) for i in range(0, len(rows), step)]
        if len(pts) < 3:
            continue
        hull = MultiPoint(pts).convex_hull
        if not isinstance(hull, Polygon) or hull.is_empty:
            continue
        hull = repair_and_clean_geometry(hull)
        area = compute_geodetic_area_km2(hull)
        if area < 0.05 or area > 80:
            continue
        values = arr[comp]
        mean_db = float(np.nanmean(values))
        min_db = float(np.nanmin(values))
        max_db = float(np.nanmax(values))
        contrast = float(p40 - mean_db)
        cy = float(np.mean(rows))
        cx = float(np.mean(cols))
        clon, clat = _pixel_to_lonlat(cy, cx, bbox, h, w)
        minx, miny, maxx, maxy = hull.bounds
        elongation = (maxx - minx) / max(maxy - miny, 1e-9)
        circularity = 4 * np.pi * area / max((compute_geodetic_perimeter_km(hull) ** 2), 1e-6)
        conf = min(0.85, max(0.25, 0.35 + 0.08 * contrast + 0.05 * min(pix / 400.0, 1.0)))
        candidates.append({
            "detection_id": f"slick-cand-{fid}",
            "label": "OIL_SLICK_CANDIDATE",
            "predicted_class": "look_alike",
            "confirmed": False,
            "geom_geojson": mapping(hull),
            "centroid_lat": round(clat, 6),
            "centroid_lon": round(clon, 6),
            "area_km2": round(area, 4),
            "perimeter_km": compute_geodetic_perimeter_km(hull),
            "confidence": round(conf, 3),
            "lookalike_risk_score": round(max(0.2, 1.0 - conf), 3),
            "statistics": {
                "mean_backscatter_db": round(mean_db, 2),
                "min_backscatter_db": round(min_db, 2),
                "max_backscatter_db": round(max_db, 2),
                "pixel_count": pix,
                "elongation": round(float(elongation), 3),
                "circularity": round(float(circularity), 3),
            },
            "method": "local_dark_spot_threshold_vv",
            "model_version": "dark-spot-mvp-v1",
            "data_status": "REAL",
        })

    candidates.sort(key=lambda c: c["area_km2"], reverse=True)
    candidates = candidates[:8]
    if not candidates:
        return {
            "status": "NO_CANDIDATE",
            "message": "No SAR dark-spot candidates met size/contrast filters in this window.",
            "candidates": [],
        }
    return {
        "status": "CANDIDATE_DETECTED",
        "message": f"{len(candidates)} oil-slick candidate(s) from SAR dark-spot analysis. Not confirmed oil.",
        "candidates": candidates,
    }
