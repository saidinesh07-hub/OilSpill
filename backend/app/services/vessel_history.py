from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.database.models import VesselSnapshot
from backend.app.intelligence.schemas import VesselRecord

class VesselHistoryService:
    def __init__(self, db: Session):
        self.db = db

    def ingest_snapshots(self, vessels: List[VesselRecord]) -> int:
        """
        Persists a batch of normalized vessels into the history table.
        Avoids duplicates by checking MMSI and exact ais_timestamp.
        """
        if not vessels:
            return 0
            
        added = 0
        for v in vessels:
            if not v.mmsi or not v.ais_timestamp:
                continue
                
            try:
                ais_dt = datetime.fromisoformat(v.ais_timestamp.replace("Z", "+00:00"))
            except ValueError:
                continue

            # Check if this exact observation exists
            exists = self.db.query(VesselSnapshot).filter(
                VesselSnapshot.mmsi == v.mmsi,
                VesselSnapshot.ais_timestamp == ais_dt
            ).first()

            if exists:
                continue

            retrieved_dt = datetime.now(timezone.utc)
            fresh_status = "UNKNOWN"
            if getattr(v, "freshness", None):
                fresh_status = v.freshness.freshness_status
                retrieved_dt = v.freshness.retrieved_at

            snapshot = VesselSnapshot(
                mmsi=v.mmsi,
                imo=v.imo,
                name=v.name,
                vessel_type=v.vessel_type,
                latitude=v.latitude,
                longitude=v.longitude,
                speed_knots=v.speed_knots,
                course_deg=v.course_deg,
                heading_deg=v.heading_deg,
                ais_timestamp=ais_dt,
                provider=v.provider,
                freshness_status=fresh_status,
                retrieved_at=retrieved_dt
            )
            self.db.add(snapshot)
            added += 1
            
        self.db.commit()
        return added
