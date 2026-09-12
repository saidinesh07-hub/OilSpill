from datetime import datetime, timezone
from typing import List, Dict, Any
from backend.app.intelligence.schemas import VesselRecord
from .schemas import OsirisVessel
from backend.app.core.logging import logger

def normalize_osiris_vessels(osiris_vessels: List[OsirisVessel]) -> List[VesselRecord]:
    """
    Converts OSIRIS raw vessel records into SeaWatch normalized VesselRecord.
    Handles invalid coordinates and missing data safely.
    """
    normalized = []
    rejected_count = 0
    
    for v in osiris_vessels:
        # Validate critical fields
        if v.lat is None or v.lng is None or not (-90.0 <= v.lat <= 90.0) or not (-180.0 <= v.lng <= 180.0):
            rejected_count += 1
            continue
            
        if v.speed is not None and v.speed < 0:
            rejected_count += 1
            continue
            
        course_deg = v.course
        if course_deg is not None and (course_deg < 0 or course_deg >= 360):
            course_deg = None
            
        iso_time = None
        try:
            # OSIRIS timestamp is epoch ms
            dt = datetime.fromtimestamp(v.timestamp / 1000.0, tz=timezone.utc)
            iso_time = dt.isoformat()
        except Exception:
            # Bad timestamp
            pass
            
        provider_name = "OSIRIS"
        if v.source:
            provider_name = f"OSIRIS-{v.source}"

        record = VesselRecord(
            mmsi=str(v.mmsi) if v.mmsi else None,
            imo=str(v.imo) if v.imo else None,
            name=v.name,
            vessel_type=v.type or "Unknown",
            latitude=v.lat,
            longitude=v.lng,
            speed_knots=v.speed,
            course_deg=course_deg,
            heading_deg=v.heading,
            destination=v.destination,
            eta=v.eta,
            ais_timestamp=iso_time,
            provider=provider_name,
            data_status="REAL"
        )
        normalized.append(record)

    logger.info(f"OSIRIS Normalization: Received {len(osiris_vessels)}, Accepted {len(normalized)}, Rejected {rejected_count}")
    return normalized
