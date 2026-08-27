import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.core.logging import logger


class InfrastructureClient:
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"

    def get_infrastructure_in_bbox(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Dict[str, Any]:
        bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"
        query = f"""
        [out:json][timeout:25];
        (
          way["man_made"="pipeline"]({bbox_str});
          way["substance"="oil"]["man_made"="pipeline"]({bbox_str});
          node["man_made"="offshore_platform"]({bbox_str});
          node["man_made"="petroleum_well"]({bbox_str});
          node["harbour"]({bbox_str});
          way["landuse"="port"]({bbox_str});
          node["industrial"="oil"]({bbox_str});
          node["amenity"="fuel"]["waterway"]({bbox_str});
          way["industrial"="refinery"]({bbox_str});
          node["seamark:type"="harbour"]({bbox_str});
        );
        out body;
        >;
        out skel qt;
        """
        retrieved = datetime.now(timezone.utc).isoformat()
        try:
            with httpx.Client(timeout=35.0) as client:
                resp = client.post(self.overpass_url, data={"data": query})
            if resp.status_code != 200:
                return {
                    "status": "ERROR",
                    "message": f"Overpass HTTP {resp.status_code}",
                    "infrastructure": [],
                    "retrieved_at": retrieved,
                }
            data = resp.json()
            nodes = {el["id"]: el for el in data.get("elements", []) if el.get("type") == "node"}
            infra: List[Dict[str, Any]] = []
            for el in data.get("elements", []):
                tags = el.get("tags") or {}
                kind = self._classify(tags)
                if not kind:
                    continue
                geom = None
                lat = el.get("lat")
                lon = el.get("lon")
                if el.get("type") == "way":
                    coords = []
                    for nid in el.get("nodes") or []:
                        n = nodes.get(nid)
                        if n and "lat" in n:
                            coords.append([n["lon"], n["lat"]])
                    if len(coords) >= 2:
                        geom = {"type": "LineString", "coordinates": coords}
                        lat = coords[len(coords) // 2][1]
                        lon = coords[len(coords) // 2][0]
                if lat is None or lon is None:
                    continue
                infra.append({
                    "id": f"{el.get('type')}/{el.get('id')}",
                    "name": tags.get("name") or f"Unnamed {kind}",
                    "type": kind,
                    "latitude": lat,
                    "longitude": lon,
                    "geometry": geom or {"type": "Point", "coordinates": [lon, lat]},
                    "tags": {k: tags[k] for k in list(tags)[:12]},
                    "source": "OpenStreetMap Overpass API",
                    "retrieved_at": retrieved,
                    "freshness": "HISTORICAL",
                    "data_status": "REAL",
                })
            return {
                "status": "COMPLETED",
                "message": f"{len(infra)} OSM feature(s).",
                "infrastructure": infra[:80],
                "retrieved_at": retrieved,
            }
        except Exception as exc:
            logger.error("Infrastructure query failed: %s", type(exc).__name__)
            return {
                "status": "ERROR",
                "message": f"Overpass request failed: {type(exc).__name__}",
                "infrastructure": [],
                "retrieved_at": retrieved,
            }

    @staticmethod
    def _classify(tags: dict) -> Optional[str]:
        if tags.get("man_made") == "pipeline" or tags.get("substance") in ("oil", "gas"):
            return "PIPELINE"
        if tags.get("man_made") == "offshore_platform":
            return "PLATFORM"
        if tags.get("man_made") == "petroleum_well":
            return "PLATFORM"
        if tags.get("industrial") == "refinery":
            return "REFINERY"
        if tags.get("landuse") == "port" or tags.get("harbour") or tags.get("seamark:type") == "harbour":
            return "PORT"
        if tags.get("industrial") == "oil":
            return "TERMINAL"
        return None
