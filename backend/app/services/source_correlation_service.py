import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from shapely.geometry import shape, Point

# Configurable Weights / Assumptions
SCORE_FRESH = 10
SCORE_RECENT = 7
SCORE_STALE = 0
SCORE_UNKNOWN = 1

def _haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _calculate_distance_to_poly(v_lat: float, v_lon: float, poly_geojson: Dict[str, Any]) -> float:
    try:
        geom = shape(poly_geojson)
        pt = Point(v_lon, v_lat)
        
        if geom.contains(pt):
            return 0.0
            
        # Simplistic conversion: 1 degree ~ 111 km
        dist_deg = geom.distance(pt)
        return dist_deg * 111.0
    except Exception:
        return 999.0

def correlate_sources(
    spill_lat: float,
    spill_lon: float,
    spill_time: Optional[str],
    spill_geojson: Optional[Dict[str, Any]],
    vessels: List[Dict[str, Any]]
) -> Dict[str, Any]:
    ranked_candidates = []
    
    if not spill_time:
        spill_time = datetime.now(timezone.utc).isoformat()
    try:
        sp_dt = datetime.fromisoformat(spill_time.replace("Z", "+00:00"))
    except ValueError:
        sp_dt = datetime.now(timezone.utc)
        
    for v in vessels:
        try:
            lat = float(v["latitude"])
            lon = float(v["longitude"])
            v_time_str = v.get("timestamp") or v.get("ais_timestamp") or ""
            v_dt = datetime.fromisoformat(v_time_str.replace("Z", "+00:00"))
        except Exception:
            continue
            
        # 1. Spatial Score (max 30)
        dist_centroid = _haversine(spill_lat, spill_lon, lat, lon)
        dist_poly = dist_centroid
        if spill_geojson:
            dist_poly = _calculate_distance_to_poly(lat, lon, spill_geojson)
            
        dist_km = min(dist_centroid, dist_poly)
        
        if dist_km <= 1.0:
            spatial_score = 30
        elif dist_km <= 5.0:
            spatial_score = 20
        elif dist_km <= 15.0:
            spatial_score = 10
        elif dist_km <= 30.0:
            spatial_score = 5
        else:
            spatial_score = 0
            
        # 2. Temporal Score (max 25)
        diff_hours = (v_dt - sp_dt).total_seconds() / 3600.0
        abs_diff = abs(diff_hours)
        
        if abs_diff <= 1.0:
            temporal_score = 25
        elif abs_diff <= 6.0:
            temporal_score = 15
        elif abs_diff <= 12.0:
            temporal_score = 8
        elif abs_diff <= 24.0:
            temporal_score = 3
        else:
            temporal_score = 0
            
        # 3. Pre-spill presence (max 15)
        # Higher score if vessel was observed BEFORE the spill detection, indicating it could have discharged
        present_before = diff_hours <= 0
        pre_spill_score = 15 if present_before and abs_diff <= 24 else 5 if not present_before and abs_diff <= 6 else 0
        
        # 4. Movement data quality (max 10)
        # MVP: no full tracks, base on speed/course presence. Not a genuine trajectory consistency.
        movement_quality_score = 10 if v.get("speed") is not None and v.get("course") is not None else 5
        
        # 5. Vessel type (max 10)
        v_type = str(v.get("vessel_type") or v.get("type") or "unknown").lower()
        if "tanker" in v_type:
            vessel_score = 10
        elif "cargo" in v_type or "container" in v_type:
            vessel_score = 7
        else:
            vessel_score = 3
            
        # 6. Freshness (max 10)
        f_status = v.get("freshness", "UNKNOWN")
        if isinstance(f_status, dict):
            f_status = f_status.get("freshness_status", "UNKNOWN")
            
        if f_status == "FRESH":
            fresh_score = SCORE_FRESH
        elif f_status == "RECENT":
            fresh_score = SCORE_RECENT
        elif f_status == "STALE":
            fresh_score = SCORE_STALE
        else:
            fresh_score = SCORE_UNKNOWN
            
        total_score = spatial_score + temporal_score + pre_spill_score + movement_quality_score + vessel_score + fresh_score
        
        classification = "HIGHLY_RELEVANT" if total_score >= 70 else "POTENTIALLY_RELEVANT" if total_score >= 40 else "NOT_RELEVANT"
        
        if classification != "NOT_RELEVANT":
            evidence = {
                "spatial_proximity": {
                    "distance_km": round(dist_km, 2),
                    "score": spatial_score
                },
                "temporal_proximity": {
                    "difference_hours": round(abs_diff, 2),
                    "score": temporal_score
                },
                "pre_spill_presence": {
                    "present_before_detection": present_before,
                    "score": pre_spill_score
                },
                "movement_data_quality": {
                    "score": movement_quality_score
                },
                "vessel_type": {
                    "type": v_type,
                    "score": vessel_score
                },
                "freshness": {
                    "status": f_status,
                    "score": fresh_score
                }
            }
            
            ranked_candidates.append({
                "mmsi": v.get("mmsi"),
                "name": v.get("name", "Unknown"),
                "correlation_score": total_score,
                "classification": classification,
                "evidence": evidence,
                "provenance": v.get("source") or v.get("provider", "UNKNOWN")
            })
            
    ranked_candidates.sort(key=lambda x: x["correlation_score"], reverse=True)
    return {
        "candidates": ranked_candidates
    }

def estimate_source_zone(slick_lat: float, slick_lon: float) -> Dict[str, Any]:
    from backend.app.services.weather_provider import WeatherProvider
    wp = WeatherProvider()
    weather = wp.get_wind_at_location(slick_lat, slick_lon)
    
    # Very rudimentary MVP backtrack based on wind direction
    # Assume slick drifted downwind at 3% of wind speed (we don't have wind speed here, just wave)
    # Using wave direction as a proxy for surface current / wind drift
    if weather.get("status") == "OK" and weather.get("wind_direction_deg") is not None:
        direction = weather.get("wind_direction_deg", 0)
        # Backtrack is opposite to the wave direction
        back_dir = (direction + 180) % 360
        # Assume 5 km drift back as an MVP guess
        dist_km = 5.0
        
        r = 6371.0
        brng = math.radians(back_dir)
        lat1 = math.radians(slick_lat)
        lon1 = math.radians(slick_lon)
        
        lat2 = math.asin(math.sin(lat1) * math.cos(dist_km/r) + math.cos(lat1) * math.sin(dist_km/r) * math.cos(brng))
        lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(dist_km/r) * math.cos(lat1), math.cos(dist_km/r) - math.sin(lat1) * math.sin(lat2))
        
        return {
            "status": "COMPLETED",
            "source_lat": math.degrees(lat2),
            "source_lon": math.degrees(lon2),
            "confidence": "MEDIUM (Based on Open-Meteo wind-wave direction)",
            "weather": weather
        }
    return {
        "status": "UNAVAILABLE",
        "source_lat": slick_lat,
        "source_lon": slick_lon,
        "confidence": "LOW (No weather data)",
        "weather": weather
    }
