"""
Temporal State Classification and Kinematics
Determines slick evolution state (Expansion, Contraction, Fragmentation, Persistence, Disappearance)
and calculates drift velocity and growth rates.
"""
from datetime import datetime
from typing import Dict, Optional
from backend.app.geospatial.geometry_ops import get_bearing_degrees, get_geodesic_distance_km


def classify_slick_evolution_state(
    prev_area_km2: float,
    curr_area_km2: float,
    match_iou: float,
    expansion_threshold: float = 0.15,
    contraction_threshold: float = -0.15
) -> str:
    """
    Classifies the physical evolution of a tracked slick between two observation timestamps.
    """
    if prev_area_km2 <= 0:
        return "PERSISTENCE"

    relative_change = (curr_area_km2 - prev_area_km2) / prev_area_km2

    if relative_change > expansion_threshold:
        return "EXPANSION"
    elif relative_change < contraction_threshold:
        return "CONTRACTION"
    else:
        return "PERSISTENCE"


def calculate_kinematics(
    prev_lon: float,
    prev_lat: float,
    prev_time: datetime,
    curr_lon: float,
    curr_lat: float,
    curr_time: datetime,
    prev_area_km2: float,
    curr_area_km2: float
) -> Dict[str, float]:
    """
    Calculates drift speed (km/h), drift heading (degrees), and area growth rate (km2/hr).
    """
    elapsed_hours = max((curr_time - prev_time).total_seconds() / 3600.0, 0.01)
    displacement_km = get_geodesic_distance_km(prev_lon, prev_lat, curr_lon, curr_lat)
    displacement_m = displacement_km * 1000.0

    drift_speed_kmh = displacement_km / elapsed_hours
    drift_heading_deg = get_bearing_degrees(prev_lon, prev_lat, curr_lon, curr_lat)

    area_delta_km2 = curr_area_km2 - prev_area_km2
    growth_rate_km2_per_hr = area_delta_km2 / elapsed_hours

    return {
        "elapsed_hours": round(elapsed_hours, 2),
        "displacement_m": round(displacement_m, 1),
        "displacement_km": round(displacement_km, 3),
        "drift_speed_kmh": round(drift_speed_kmh, 3),
        "drift_heading_deg": round(drift_heading_deg, 1),
        "area_delta_km2": round(area_delta_km2, 4),
        "growth_rate_km2_per_hr": round(growth_rate_km2_per_hr, 4)
    }
