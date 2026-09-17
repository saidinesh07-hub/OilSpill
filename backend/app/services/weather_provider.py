import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.core.logging import logger

class WeatherProvider:
    """Fetches real wind data from Open-Meteo (No API key required for MVP)"""
    def __init__(self):
        self.base_url = "https://marine-api.open-meteo.com/v1/marine"

    def get_wind_at_location(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch current wind speed, direction, and wave height at location."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "wave_height,wave_direction,wave_period,wind_wave_height,wind_wave_direction,wind_wave_period",
            "timezone": "UTC"
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(self.base_url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    current = data.get("current", {})
                    return {
                        "status": "OK",
                        "wave_height_m": current.get("wave_height"),
                        "wind_direction_deg": current.get("wind_wave_direction"),
                        "source": "Open-Meteo Marine API",
                        "timestamp": current.get("time") or datetime.now(timezone.utc).isoformat()
                    }
                else:
                    return {"status": "UNAVAILABLE", "message": f"HTTP {res.status_code}"}
        except Exception as e:
            logger.error(f"Weather provider error: {e}")
            return {"status": "UNAVAILABLE", "message": str(e)}
