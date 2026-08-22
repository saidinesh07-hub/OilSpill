"""
Impact Assessment and Spatiotemporal Asset Intersection Engine
Calculates probabilistic overlap, arrival windows, distance to slick, and exposure severity.
"""
from typing import Any, Dict, List
import numpy as np
from shapely.geometry import shape
from backend.app.core.logging import logger
from backend.app.geospatial.geometry_ops import compute_geodetic_area_km2, get_geodesic_distance_km


class ImpactAnalyzer:
    """
    Evaluates exposure of sensitive assets against multi-horizon forecast uncertainty bands.
    """
    @staticmethod
    def assess_impacts(
        forecast_bands: List[Dict[str, Any]],
        assets: List[Dict[str, Any]],
        current_slick_lon: float,
        current_slick_lat: float
    ) -> List[Dict[str, Any]]:
        """
        Intersects forecast bands (50%, 80%, 95%) with assets across all horizons (6, 12, 24, 48h).
        
        Returns list of impact assessments per asset.
        """
        impact_results = []

        # Sort bands by horizon (earliest first)
        sorted_bands = sorted(forecast_bands, key=lambda b: (b["horizon_hours"], b["confidence_level"]))

        for asset in assets:
            asset_geom = shape(asset["geom_geojson"])
            a_lon = asset["centroid_lon"]
            a_lat = asset["centroid_lat"]
            
            # Baseline distance from current slick position
            dist_to_slick_km = get_geodesic_distance_km(current_slick_lon, current_slick_lat, a_lon, a_lat)

            earliest_impact_h = None
            max_impact_prob = 0.0
            intersected_area_km2 = 0.0
            impacted_band_horizon = 48

            for band in sorted_bands:
                band_geom = shape(band["geom_geojson"])
                
                if band_geom.intersects(asset_geom):
                    h = band["horizon_hours"]
                    conf = band["confidence_level"]

                    # Impact probability assignment based on containment band:
                    # Inside 50% band (core best-guess) -> prob = 0.90
                    # Inside 80% band -> prob = 0.70
                    # Inside 95% band (outer envelope) -> prob = 0.40
                    if conf <= 0.50:
                        band_prob = 0.90
                    elif conf <= 0.80:
                        band_prob = 0.70
                    else:
                        band_prob = 0.40

                    if band_prob > max_impact_prob:
                        max_impact_prob = band_prob
                        impacted_band_horizon = h

                    if earliest_impact_h is None:
                        earliest_impact_h = float(h)

                    # Compute intersection geometry area
                    try:
                        inter = band_geom.intersection(asset_geom)
                        if not inter.is_empty:
                            area_k = compute_geodetic_area_km2(inter)
                            intersected_area_km2 = max(intersected_area_km2, area_k)
                    except Exception:
                        pass

            # If no direct intersection within 48h, compute distance-decayed potential exposure
            if max_impact_prob == 0.0:
                if dist_to_slick_km < 15.0:
                    max_impact_prob = float(max(0.05, 0.35 * (1.0 - (dist_to_slick_km / 15.0))))
                    earliest_impact_h = round(dist_to_slick_km / 0.8, 1)  # Est. ~0.8 km/h drift
                else:
                    max_impact_prob = 0.0
                    earliest_impact_h = 72.0

            # Determine exposure level category
            if max_impact_prob >= 0.75:
                exposure = "CRITICAL"
            elif max_impact_prob >= 0.50:
                exposure = "HIGH"
            elif max_impact_prob >= 0.25:
                exposure = "MODERATE"
            elif max_impact_prob > 0.05:
                exposure = "LOW"
            else:
                exposure = "NEGLIGIBLE"

            impact_results.append({
                "asset_id": asset.get("asset_id", asset.get("name")),
                "asset_name": asset["name"],
                "asset_type": asset["asset_type"],
                "sensitivity_weight": asset.get("sensitivity_weight", 1.0),
                "horizon_hours": impacted_band_horizon,
                "impact_probability": round(max_impact_prob, 3),
                "earliest_time_to_impact_hours": round(earliest_impact_h or 48.0, 1),
                "distance_to_slick_km": round(dist_to_slick_km, 2),
                "intersected_area_km2": round(intersected_area_km2, 3),
                "exposure_level": exposure
            })

        # Sort by urgency (earliest arrival window & highest probability)
        impact_results.sort(key=lambda x: (-x["impact_probability"], x["earliest_time_to_impact_hours"]))
        return impact_results
