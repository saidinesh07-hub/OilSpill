import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.intelligence.schemas import VesselRecord, Freshness

from backend.app.services.osiris.client import OsirisClient
from backend.app.services.osiris.maritime import normalize_osiris_vessels
from backend.app.services.ais_client import AISClient

class MaritimeResponse(BaseModel):
    status: str
    provider: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    retrieved_at: str
    vessel_count: int = 0
    vessels: List[VesselRecord] = Field(default_factory=list)


def _determine_freshness(ais_timestamp: Optional[str]) -> str:
    if not ais_timestamp:
        return "UNKNOWN"
    try:
        dt = datetime.fromisoformat(ais_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff_minutes = (now - dt).total_seconds() / 60.0
        if diff_minutes < 5:
            return "FRESH"
        elif diff_minutes < 30:
            return "RECENT"
        elif diff_minutes < 360:
            return "STALE"
        else:
            return "STALE"
    except Exception:
        return "UNKNOWN"


def _filter_by_bbox(vessels: List[VesselRecord], min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> List[VesselRecord]:
    filtered = []
    for v in vessels:
        if v.latitude is not None and v.longitude is not None:
            if min_lat <= v.latitude <= max_lat and min_lon <= v.longitude <= max_lon:
                filtered.append(v)
    return filtered


class MaritimeOrchestrator:
    def __init__(self):
        self.osiris_client = OsirisClient()
        self.aishub_client = AISClient()
        self.demo_enabled = getattr(settings, "DATA_MODE", "REAL") == "DEMO"

    async def get_vessels(
        self, 
        min_lat: Optional[float] = None, 
        min_lon: Optional[float] = None, 
        max_lat: Optional[float] = None, 
        max_lon: Optional[float] = None, 
        limit: int = 1000
    ) -> MaritimeResponse:
        
        now_str = datetime.now(timezone.utc).isoformat()
        has_bbox = (min_lat is not None and min_lon is not None and max_lat is not None and max_lon is not None)
        
        # 1. Try OSIRIS
        logger.info("Attempting OSIRIS for maritime data.")
        osiris_status, osiris_data = await self.osiris_client.fetch_maritime_data()
        
        if osiris_status == "SUCCESS" and osiris_data is not None:
            vessels = normalize_osiris_vessels(osiris_data.ships)
            if has_bbox:
                vessels = _filter_by_bbox(vessels, min_lat, min_lon, max_lat, max_lon)
                
            # Apply freshness
            for v in vessels:
                v.freshness = Freshness(
                    source=v.provider,
                    retrieved_at=datetime.fromisoformat(now_str.replace("Z", "+00:00")),
                    freshness_status=_determine_freshness(v.ais_timestamp)
                )
                
            vessels = vessels[:limit]
            return MaritimeResponse(
                status="SUCCESS",
                provider="OSIRIS",
                fallback_used=False,
                retrieved_at=now_str,
                vessel_count=len(vessels),
                vessels=vessels
            )
            
        fallback_reason = f"OSIRIS_{osiris_status}"
        logger.warning(f"OSIRIS unavailable ({fallback_reason}), falling back to AISHUB.")
        
        # 2. Fallback to AISHUB
        if has_bbox:
            # AISHUB client requires bbox
            aishub_res = self.aishub_client.get_vessels_in_bbox(min_lon, min_lat, max_lon, max_lat)
            if aishub_res.get("status") == "COMPLETED":
                raw_aishub = aishub_res.get("vessels", [])
                vessels = []
                for v in raw_aishub:
                    vr = VesselRecord(
                        mmsi=str(v.get("mmsi")) if v.get("mmsi") else None,
                        imo=str(v.get("imo")) if v.get("imo") else None,
                        name=v.get("name"),
                        vessel_type=v.get("vessel_type", "Unknown"),
                        latitude=v.get("latitude"),
                        longitude=v.get("longitude"),
                        speed_knots=v.get("speed"),
                        heading_deg=v.get("heading"),
                        ais_timestamp=v.get("timestamp"),
                        provider="AISHUB",
                        data_status="REAL"
                    )
                    vr.freshness = Freshness(
                        source="AISHUB",
                        retrieved_at=datetime.fromisoformat(now_str.replace("Z", "+00:00")),
                        freshness_status=_determine_freshness(vr.ais_timestamp)
                    )
                    vessels.append(vr)
                
                vessels = vessels[:limit]
                return MaritimeResponse(
                    status="SUCCESS",
                    provider="AISHUB",
                    fallback_used=True,
                    fallback_reason=fallback_reason,
                    retrieved_at=now_str,
                    vessel_count=len(vessels),
                    vessels=vessels
                )
        else:
            logger.warning("AISHUB requires bbox, skipping AISHUB fallback.")
        
        # 3. Fallback to DEMO if explicitly enabled
        if self.demo_enabled:
            logger.warning("Live providers failed. Falling back to DEMO_DATA because DATA_MODE=DEMO.")
            vr = VesselRecord(
                mmsi="DEMO0001",
                name="DEMO TANKER ALPHA",
                vessel_type="Tanker (DEMO)",
                latitude=min_lat + 0.03 if has_bbox else 0.0,
                longitude=min_lon + 0.05 if has_bbox else 0.0,
                speed_knots=8.2,
                heading_deg=120.0,
                ais_timestamp=now_str,
                provider="DEMO_DATA",
                data_status="DEMO"
            )
            vr.freshness = Freshness(
                source="DEMO_DATA",
                retrieved_at=datetime.fromisoformat(now_str.replace("Z", "+00:00")),
                freshness_status="FRESH"
            )
            vessels = [vr]
            return MaritimeResponse(
                status="SUCCESS",
                provider="DEMO_DATA",
                fallback_used=True,
                fallback_reason="LIVE_UNAVAILABLE",
                retrieved_at=now_str,
                vessel_count=len(vessels),
                vessels=vessels
            )
            
        logger.error("All maritime providers unavailable. Returning UNAVAILABLE.")
        return MaritimeResponse(
            status="UNAVAILABLE",
            provider=None,
            fallback_used=True,
            fallback_reason="ALL_LIVE_PROVIDERS_FAILED",
            retrieved_at=now_str,
            vessel_count=0,
            vessels=[]
        )
