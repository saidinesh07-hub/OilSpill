"""
Raster to Vector Polygonization Pipeline
Converts neural segmentation raster masks into georeferenced polygons with calibrated confidence.
"""
from typing import Any, Dict, List, Tuple
import numpy as np
from scipy.ndimage import label, find_objects
from shapely.geometry import Polygon, MultiPolygon, mapping
from backend.app.geospatial.projections import AffineGeoTransform
from backend.app.geospatial.geometry_ops import (
    compute_geodetic_area_km2,
    compute_geodetic_perimeter_km,
    repair_and_clean_geometry
)
from backend.app.ml.constants import CLASS_ID_TO_NAME


def extract_polygon_contours_from_binary_mask(
    binary_mask: np.ndarray,
    transform: AffineGeoTransform,
    min_pixels: int = 15
) -> List[Tuple[Polygon, np.ndarray]]:
    """
    Extracts georeferenced Shapely polygons for connected components in a binary mask.
    """
    labeled_array, num_features = label(binary_mask)
    if num_features == 0:
        return []

    polygons_with_masks = []
    
    for feature_id in range(1, num_features + 1):
        component_mask = (labeled_array == feature_id)
        pixel_count = np.sum(component_mask)
        if pixel_count < min_pixels:
            continue

        # Find coordinates of boundary pixels
        y_indices, x_indices = np.where(component_mask)
        if len(y_indices) < 3:
            continue

        # Create convex hull or bounding polygon from coordinate points
        geo_points = []
        # Sample boundary perimeter points
        step = max(1, len(y_indices) // 60)
        for i in range(0, len(y_indices), step):
            lon, lat = transform.pixel_to_geo(y_indices[i], x_indices[i])
            geo_points.append((lon, lat))

        if len(geo_points) < 3:
            continue

        # Build Polygon via convex hull or simplified boundary
        from shapely.geometry import MultiPoint
        mp = MultiPoint(geo_points)
        poly = mp.convex_hull

        if isinstance(poly, Polygon) and not poly.is_empty and poly.is_valid:
            poly = repair_and_clean_geometry(poly)
            polygons_with_masks.append((poly, component_mask))

    return polygons_with_masks


def polygonize_segmentation_output(
    class_mask: np.ndarray,
    prob_maps: np.ndarray,
    transform: AffineGeoTransform,
    min_area_km2: float = 0.05,
    model_version: str = "deeplabv3plus-v1.0"
) -> List[Dict[str, Any]]:
    """
    Converts full-scene 5-class segmentation output to georeferenced polygon detections.
    
    Returns list of detection dictionaries ready for DB storage and GeoJSON export.
    """
    detections = []
    # Target classes: 1 = oil_spill, 2 = look_alike
    target_classes = [1, 2]

    for class_id in target_classes:
        class_name = CLASS_ID_TO_NAME[class_id]
        binary_mask = (class_mask == class_id).astype(np.uint8)
        
        extracted = extract_polygon_contours_from_binary_mask(
            binary_mask=binary_mask,
            transform=transform,
            min_pixels=20
        )

        for poly, comp_mask in extracted:
            area_km2 = compute_geodetic_area_km2(poly)
            if area_km2 < min_area_km2:
                continue

            perim_km = compute_geodetic_perimeter_km(poly)
            centroid = poly.centroid
            centroid_lon = round(centroid.x, 7)
            centroid_lat = round(centroid.y, 7)

            # Extract calibrated confidence from probability field within component mask
            class_probs = prob_maps[:, :, class_id][comp_mask]
            mean_conf = float(np.mean(class_probs)) if len(class_probs) > 0 else 0.85

            # Calculate look-alike risk (cross-entropy confusion score)
            lookalike_probs = prob_maps[:, :, 2][comp_mask]
            mean_lookalike_conf = float(np.mean(lookalike_probs)) if len(lookalike_probs) > 0 else 0.15

            # Morphology descriptors
            # Circularity = 4 * pi * Area / Perimeter^2 (1.0 = circle, <0.2 = elongated slick plume)
            circularity = float(4.0 * np.pi * (area_km2) / max(perim_km ** 2, 1e-5))
            circularity = min(1.0, circularity)

            detections.append({
                "geom_geojson": mapping(poly),
                "centroid_lat": centroid_lat,
                "centroid_lon": centroid_lon,
                "area_km2": area_km2,
                "perimeter_km": perim_km,
                "predicted_class": class_name,
                "confidence": round(mean_conf, 3),
                "lookalike_risk_score": round(mean_lookalike_conf, 3),
                "morphology_features": {
                    "circularity": round(circularity, 3),
                    "is_elongated_plume": bool(circularity < 0.35),
                    "pixel_count": int(np.sum(comp_mask))
                },
                "model_version": model_version
            })

    return detections
