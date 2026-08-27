"""Geocoding via OpenStreetMap Nominatim. No hardcoded city coordinates."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from shapely.geometry import mapping, box
from backend.app.core.config import settings
from backend.app.intelligence.http_util import fetch_json
from backend.app.intelligence.schemas import LocationFix, ProviderStatus


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def _parse_lat_lon(query: str) -> Optional[tuple]:
    text = query.strip().replace(";", ",")
    if "," in text:
        parts = [p.strip() for p in text.split(",")]
        if len(parts) == 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return lat, lon
            except ValueError:
                return None
    tokens = text.split()
    if len(tokens) == 2:
        try:
            lat = float(tokens[0])
            lon = float(tokens[1])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except ValueError:
            return None
    return None


def aoi_from_point(lat: float, lon: float, radius_km: float) -> tuple:
    # ~1 deg lat = 111 km; lon scaled by cos(lat)
    import math
    dlat = radius_km / 111.0
    dlon = radius_km / max(111.0 * math.cos(math.radians(lat)), 20.0)
    min_lon, min_lat, max_lon, max_lat = lon - dlon, lat - dlat, lon + dlon, lat + dlat
    geom = mapping(box(min_lon, min_lat, max_lon, max_lat))
    return [min_lon, min_lat, max_lon, max_lat], geom


class NominatimGeocodingProvider:
    name = "nominatim_osm"

    def geocode(self, query: str, radius_km: float = 25.0) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        parsed = _parse_lat_lon(query)
        if parsed:
            lat, lon = parsed
            bbox, aoi = aoi_from_point(lat, lon, radius_km)
            loc = LocationFix(
                query=query,
                name=f"{lat:.4f}, {lon:.4f}",
                latitude=lat,
                longitude=lon,
                display_name="Coordinate pair",
                bbox=bbox,
                aoi_geojson=aoi,
                radius_km=radius_km,
                source="user_coordinates",
                retrieved_at=now,
                data_status="REAL",
            )
            status = ProviderStatus(
                provider=self.name,
                available=True,
                status="OK",
                message="Interpreted as latitude, longitude.",
                data_status="REAL",
            )
            return {"location": loc, "status": status, "candidates": [loc.model_dump(mode="json")]}

        headers = {"User-Agent": getattr(settings, "NOMINATIM_USER_AGENT", settings.NOMINATIM_USER_AGENT), "Accept": "application/json"}
        result = fetch_json(
            "GET",
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 5, "addressdetails": 0},
            headers=headers,
            timeout=20.0,
        )
        if not result["ok"]:
            status = ProviderStatus(
                provider=self.name,
                available=False,
                status="UNAVAILABLE",
                message=f"Geocoding failed: {result.get('error')}",
                http_status=result.get("status_code"),
                data_status="UNAVAILABLE",
            )
            return {"location": None, "status": status, "candidates": []}

        rows = result["data"] or []
        if not isinstance(rows, list) or not rows:
            status = ProviderStatus(
                provider=self.name,
                available=True,
                status="EMPTY",
                message="No geocoding matches for that query.",
                data_status="REAL",
            )
            return {"location": None, "status": status, "candidates": []}

        candidates = []
        for row in rows:
            try:
                lat = float(row["lat"])
                lon = float(row["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            bbox, aoi = aoi_from_point(lat, lon, radius_km)
            candidates.append(
                LocationFix(
                    query=query,
                    name=row.get("display_name") or query,
                    latitude=lat,
                    longitude=lon,
                    display_name=row.get("display_name"),
                    bbox=bbox,
                    aoi_geojson=aoi,
                    radius_km=radius_km,
                    source=self.name,
                    retrieved_at=now,
                    data_status="REAL",
                )
            )
        if not candidates:
            status = ProviderStatus(
                provider=self.name,
                available=True,
                status="EMPTY",
                message="Geocoder returned unusable rows.",
                data_status="REAL",
            )
            return {"location": None, "status": status, "candidates": []}

        status = ProviderStatus(
            provider=self.name,
            available=True,
            status="OK",
            message=f"Resolved via OpenStreetMap Nominatim ({len(candidates)} match(es)).",
            data_status="REAL",
        )
        return {
            "location": candidates[0],
            "status": status,
            "candidates": [c.model_dump(mode="json") for c in candidates],
        }
