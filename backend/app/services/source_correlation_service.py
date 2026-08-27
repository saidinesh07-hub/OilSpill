"""Explainable source correlation. Proximity is not causation."""
from typing import Any, Dict, List, Optional
from datetime import datetime
import math


def _haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _hours(t1: str, t2: Optional[str]) -> Optional[float]:
    if not t1 or not t2:
        return None
    try:
        d1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
        d2 = datetime.fromisoformat(str(t2).replace("Z", "+00:00"))
        return abs((d1 - d2).total_seconds()) / 3600.0
    except Exception:
        return None

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


def correlate_sources(
    slick_lat: float,
    slick_lon: float,
    slick_time: Optional[str],
    vessels: List[Dict[str, Any]],
    infrastructure: List[Dict[str, Any]],
    slick_detected: bool,
) -> Dict[str, Any]:
    ranked: List[Dict[str, Any]] = []
    ref = "slick candidate centroid" if slick_detected else "AOI center (no slick candidate)"

    for v in vessels:
        try:
            lat, lon = float(v["latitude"]), float(v["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        dist = _haversine(slick_lat, slick_lon, lat, lon)
        if dist > 25:
            continue
        dt = _hours(slick_time or "", v.get("timestamp") or v.get("ais_timestamp"))
        dist_pts = 30 if dist < 2 else 22 if dist < 5 else 12 if dist < 10 else 5
        time_pts = 0
        if dt is None:
            time_note = "Temporal evidence not available"
        elif dt < 1:
            time_pts = 25
            time_note = f"{dt:.2f} h from acquisition"
        elif dt < 6:
            time_pts = 15
            time_note = f"{dt:.1f} h from acquisition"
        elif dt < 24:
            time_pts = 6
            time_note = f"{dt:.1f} h from acquisition"
        else:
            time_note = f"{dt:.1f} h from acquisition (weak)"
        fresh_pts = 8 if (dt is not None and dt < 1) else 3
        score = dist_pts + time_pts + fresh_pts
        level = "HIGH" if score >= 50 else "MEDIUM" if score >= 30 else "LOW"
        ranked.append({
            "type": "VESSEL",
            "name": v.get("name") or "Unknown vessel",
            "mmsi": v.get("mmsi"),
            "distance_km": round(dist, 2),
            "evidence_score": score,
            "assessment": "POTENTIAL VESSEL-RELATED SOURCE" if score >= 30 else "NEARBY VESSEL — INSUFFICIENT EVIDENCE OF CAUSATION",
            "spatial_proximity": f"{dist:.1f} km from {ref}",
            "temporal_relationship": time_note,
            "track_relationship": "Current AIS position only (no historical track in this MVP)",
            "data_freshness": v.get("timestamp") or v.get("ais_timestamp"),
            "source": v.get("source"),
            "score_breakdown": {
                "distance_contribution": dist_pts,
                "temporal_relevance": time_pts,
                "data_freshness": fresh_pts,
                "track_intersection": 0,
            },
            "confidence": level,
            "caveat": "Spatial/temporal correlation is not proof of causation.",
        })

    for inf in infrastructure:
        try:
            lat, lon = float(inf["latitude"]), float(inf["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        dist = _haversine(slick_lat, slick_lon, lat, lon)
        if dist > 25:
            continue
        dist_pts = 28 if dist < 1 else 18 if dist < 5 else 8 if dist < 15 else 3
        score = dist_pts
        level = "MEDIUM" if dist < 2 else "LOW"
        ranked.append({
            "type": inf.get("type") or "INFRASTRUCTURE",
            "name": inf.get("name") or "Unnamed feature",
            "distance_km": round(dist, 2),
            "evidence_score": score,
            "assessment": "NEARBY INFRASTRUCTURE — INSUFFICIENT EVIDENCE OF CAUSATION",
            "spatial_proximity": f"{dist:.1f} km from {ref}",
            "temporal_relationship": "NOT AVAILABLE (static OSM feature)",
            "track_relationship": "n/a",
            "data_freshness": inf.get("retrieved_at"),
            "source": inf.get("source"),
            "score_breakdown": {
                "distance_contribution": dist_pts,
                "temporal_relevance": 0,
                "data_freshness": 0,
                "track_intersection": 0,
            },
            "confidence": level,
            "caveat": "A nearby pipeline or port does not establish a leak or discharge.",
        })

    ranked.sort(key=lambda x: -x["evidence_score"])
    if not ranked:
        conclusion = (
            "No nearby vessels or infrastructure were available to correlate with the analysis location. "
            "Source remains undetermined."
        )
    elif not slick_detected:
        conclusion = (
            "No oil-slick candidate was extracted from the SAR window. Nearby objects are listed for context only "
            "and are not spill-source evidence."
        )
    else:
        top = ranked[0]
        conclusion = (
            f"SAR dark-spot analysis produced an oil-slick candidate. The highest-ranked object is "
            f"{top['type']} '{top['name']}' at {top['distance_km']} km ({top['assessment']}). "
            "This is a potential source relationship and does not establish causation."
        )

    return {
        "candidates": ranked[:12],
        "conclusion": conclusion,
        "limitations": [
            "Low SAR backscatter can be oil, low wind, rain, or other look-alikes.",
            "AIS coverage is incomplete; absence of vessels is not proof of no vessels.",
            "OSM infrastructure can be incomplete or outdated.",
            "No historical AIS track intersection was computed unless a track was provided.",
            "Do not interpret proximity as legal or causal determination.",
        ],
        "reference_point": ref,
    }
