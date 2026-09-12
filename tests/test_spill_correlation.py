import pytest
from datetime import datetime, timedelta, timezone
from backend.app.services.source_correlation_service import correlate_sources
from backend.app.services.vessel_history import VesselHistoryService
from backend.app.intelligence.schemas import VesselRecord, Freshness
from backend.app.database.models import VesselSnapshot
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database.session import Base

# Setup in-memory sqlite for history testing
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def test_vessel_history_ingestion():
    db = SessionLocal()
    history_service = VesselHistoryService(db)
    
    # 1. Ingest new
    now_str = datetime.now(timezone.utc).isoformat()
    vr1 = VesselRecord(
        mmsi="123456", name="TEST", latitude=10.0, longitude=20.0,
        ais_timestamp=now_str, provider="OSIRIS", data_status="REAL"
    )
    vr1.freshness = Freshness(source="OSIRIS", retrieved_at=datetime.now(timezone.utc), freshness_status="FRESH")
    
    added = history_service.ingest_snapshots([vr1])
    assert added == 1
    
    # 2. Ingest duplicate (same mmsi, same timestamp)
    added = history_service.ingest_snapshots([vr1])
    assert added == 0
    
    # 3. Ingest new timestamp
    later_str = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    vr2 = VesselRecord(
        mmsi="123456", name="TEST", latitude=10.1, longitude=20.1,
        ais_timestamp=later_str, provider="OSIRIS", data_status="REAL"
    )
    added = history_service.ingest_snapshots([vr2])
    assert added == 1
    
    count = db.query(VesselSnapshot).count()
    assert count == 2
    db.close()

def test_correlation_spatial_and_vessel_type():
    spill_lat, spill_lon = 10.0, 20.0
    spill_time = datetime.now(timezone.utc).isoformat()
    
    vessels = [
        # Exactly at spill, tanker
        {"mmsi": "1", "latitude": 10.0, "longitude": 20.0, "timestamp": spill_time, "vessel_type": "tanker", "freshness": "FRESH", "speed": 10, "course": 90},
        # Far from spill
        {"mmsi": "2", "latitude": 15.0, "longitude": 25.0, "timestamp": spill_time, "vessel_type": "tanker", "freshness": "FRESH"}
    ]
    
    res = correlate_sources(spill_lat, spill_lon, spill_time, None, vessels)
    assert len(res["candidates"]) == 2
    
    c1 = res["candidates"][0]
    c2 = res["candidates"][1]
    
    assert c1["mmsi"] == "1"
    assert c1["evidence"]["spatial_proximity"]["score"] == 30
    assert c1["evidence"]["vessel_type"]["score"] == 10
    
    assert c2["mmsi"] == "2"
    assert c2["evidence"]["spatial_proximity"]["score"] == 0

def test_correlation_temporal_and_freshness_regression():
    spill_lat, spill_lon = 10.0, 20.0
    spill_time_dt = datetime.now(timezone.utc)
    spill_time = spill_time_dt.isoformat()
    
    # Before spill
    v_before = (spill_time_dt - timedelta(hours=2)).isoformat()
    # After spill
    v_after = (spill_time_dt + timedelta(hours=2)).isoformat()
    
    vessels = [
        {"mmsi": "BEFORE", "latitude": 10.0, "longitude": 20.0, "timestamp": v_before, "freshness": "STALE"},
        {"mmsi": "AFTER_FRESH", "latitude": 10.0, "longitude": 20.0, "timestamp": v_after, "freshness": "FRESH"},
        {"mmsi": "AFTER_RECENT", "latitude": 10.0, "longitude": 20.0, "timestamp": v_after, "freshness": "RECENT"}
    ]
    
    res = correlate_sources(spill_lat, spill_lon, spill_time, None, vessels)
    
    cand_before = next(c for c in res["candidates"] if c["mmsi"] == "BEFORE")
    cand_after_fresh = next(c for c in res["candidates"] if c["mmsi"] == "AFTER_FRESH")
    cand_after_recent = next(c for c in res["candidates"] if c["mmsi"] == "AFTER_RECENT")
    
    # Before gets pre_spill points
    assert cand_before["evidence"]["pre_spill_presence"]["score"] > cand_after_fresh["evidence"]["pre_spill_presence"]["score"]
    
    # Freshness configured scores regression:
    assert cand_after_fresh["evidence"]["freshness"]["score"] == 10
    assert cand_after_recent["evidence"]["freshness"]["score"] == 7
    assert cand_before["evidence"]["freshness"]["score"] == 0

def test_movement_data_quality_renaming():
    spill_lat, spill_lon = 10.0, 20.0
    spill_time = datetime.now(timezone.utc).isoformat()
    
    vessels = [
        {"mmsi": "V1", "latitude": 10.0, "longitude": 20.0, "timestamp": spill_time, "speed": 10, "course": 90},
        {"mmsi": "V2", "latitude": 10.0, "longitude": 20.0, "timestamp": spill_time} # Missing speed/course
    ]
    
    res = correlate_sources(spill_lat, spill_lon, spill_time, None, vessels)
    cand_full = next(c for c in res["candidates"] if c["mmsi"] == "V1")
    cand_missing = next(c for c in res["candidates"] if c["mmsi"] == "V2")
    
    # Verify the key is renamed properly and scores match the data presence
    assert "movement_data_quality" in cand_full["evidence"]
    assert "track_consistency" not in cand_full["evidence"]
    
    assert cand_full["evidence"]["movement_data_quality"]["score"] == 10
    assert cand_missing["evidence"]["movement_data_quality"]["score"] == 5

def test_missing_data_handling():
    spill_lat, spill_lon = 10.0, 20.0
    spill_time = datetime.now(timezone.utc).isoformat()
    
    vessels = [
        # Missing lat/lon -> ignored
        {"mmsi": "NO_LOC", "timestamp": spill_time},
        # Missing timestamp -> fallback parsing or 0 score
        {"mmsi": "NO_TIME", "latitude": 10.0, "longitude": 20.0}
    ]
    
    res = correlate_sources(spill_lat, spill_lon, spill_time, None, vessels)
    # Both skipped because missing required lat/lon or datetime fails
    assert len(res["candidates"]) == 0
