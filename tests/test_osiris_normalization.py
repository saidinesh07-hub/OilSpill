import pytest
from backend.app.services.osiris.schemas import OsirisVessel
from backend.app.services.osiris.maritime import normalize_osiris_vessels

def test_normalization_success():
    raw_vessels = [
        OsirisVessel(
            mmsi=123, imo=456, timestamp=1700000000000, name="TEST",
            lat=10.0, lng=20.0, speed=15.5, course=90.0,
            heading=95.0, type="tanker", source="Kpler"
        )
    ]
    normalized = normalize_osiris_vessels(raw_vessels)
    assert len(normalized) == 1
    assert normalized[0].mmsi == "123"
    assert normalized[0].imo == "456"
    assert normalized[0].name == "TEST"
    assert normalized[0].vessel_type == "tanker"
    assert normalized[0].latitude == 10.0
    assert normalized[0].longitude == 20.0
    assert normalized[0].speed_knots == 15.5
    assert normalized[0].course_deg == 90.0
    assert normalized[0].heading_deg == 95.0
    # 1700000000000 ms is 2023-11-14T22:13:20+00:00
    assert "2023-11-14T" in normalized[0].ais_timestamp
    assert normalized[0].provider == "OSIRIS-Kpler"

def test_invalid_latitude():
    raw_vessels = [OsirisVessel(timestamp=0, lat=95.0, lng=0.0)]
    normalized = normalize_osiris_vessels(raw_vessels)
    assert len(normalized) == 0

def test_invalid_longitude():
    raw_vessels = [OsirisVessel(timestamp=0, lat=0.0, lng=200.0)]
    normalized = normalize_osiris_vessels(raw_vessels)
    assert len(normalized) == 0
    
def test_negative_speed():
    raw_vessels = [OsirisVessel(timestamp=0, lat=0.0, lng=0.0, speed=-5.0)]
    normalized = normalize_osiris_vessels(raw_vessels)
    assert len(normalized) == 0
    
def test_invalid_course():
    raw_vessels = [OsirisVessel(timestamp=0, lat=0.0, lng=0.0, course=400.0)]
    normalized = normalize_osiris_vessels(raw_vessels)
    assert len(normalized) == 1
    assert normalized[0].course_deg is None

def test_missing_optional_fields():
    raw_vessels = [OsirisVessel(timestamp=1700000000000, lat=10.0, lng=20.0)]
    normalized = normalize_osiris_vessels(raw_vessels)
    assert len(normalized) == 1
    assert normalized[0].name is None
    assert normalized[0].vessel_type == "other"
    assert normalized[0].provider == "OSIRIS"

def test_multiple_vessels_where_one_is_malformed():
    raw_vessels = [
        OsirisVessel(timestamp=0, lat=10.0, lng=20.0),
        OsirisVessel(timestamp=0, lat=100.0, lng=20.0) # invalid lat
    ]
    normalized = normalize_osiris_vessels(raw_vessels)
    assert len(normalized) == 1
    assert normalized[0].latitude == 10.0
