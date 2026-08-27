import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.core.config import settings
from backend.app.core.logging import logger

class AISClient:
    def __init__(self):
        self.username = settings.AISHUB_USERNAME
        self.api_url = settings.AIS_API_URL or "https://data.aishub.net/ws.php"

    def get_vessels_in_bbox(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Dict[str, Any]:
        """
        Query AISHUB for real vessels.
        """
        if not self.username:
            return {
                "status": "UNAVAILABLE",
                "message": "AIS unavailable — configure AIS provider",
                "vessels": []
            }

        params = {
            "username": self.username,
            "format": 1,
            "output": "json",
            "compress": 0,
            "latmin": min_lat,
            "latmax": max_lat,
            "lonmin": min_lon,
            "lonmax": max_lon
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(self.api_url, params=params)
                if resp.status_code != 200:
                    return {
                        "status": "ERROR",
                        "message": f"AIS API returned HTTP {resp.status_code}",
                        "vessels": []
                    }
                data = resp.json()
                
                if data[0].get("ERROR"):
                    return {
                        "status": "ERROR",
                        "message": f"AIS API Error: {data[0].get('ERROR')}",
                        "vessels": []
                    }
                
                # AISHUB format: [{"MMSI": ..., "TIME": ..., "LONGITUDE": ..., "LATITUDE": ..., "COG": ..., "SOG": ..., "HEADING": ..., ...}]
                raw_vessels = data[1]
                vessels = []
                for v in raw_vessels:
                    vessels.append({
                        "mmsi": v.get("MMSI"),
                        "name": v.get("NAME", "Unknown"),
                        "imo": v.get("IMO"),
                        "latitude": v.get("LATITUDE"),
                        "longitude": v.get("LONGITUDE"),
                        "heading": v.get("HEADING"),
                        "speed": v.get("SOG"),
                        "vessel_type": v.get("TYPE"),
                        "timestamp": datetime.fromtimestamp(v.get("TIME", 0), tz=timezone.utc).isoformat(),
                        "source": "AISHUB (Live)",
                        "freshness": "LIVE_API"
                    })
                
                return {
                    "status": "COMPLETED",
                    "vessels": vessels
                }

        except Exception as e:
            logger.error(f"AIS query failed: {e}")
            return {
                "status": "ERROR",
                "message": str(e),
                "vessels": []
            }
