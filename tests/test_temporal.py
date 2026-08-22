"""
Unit Tests for Temporal Association, Hungarian Tracking, and Kinematics
"""
from datetime import datetime, timezone, timedelta
import pytest
from backend.app.temporal.tracker import MultiTemporalSlickTracker
from backend.app.temporal.evolution import classify_slick_evolution_state, calculate_kinematics


def test_evolution_state_classification():
    # 20% area growth -> EXPANSION
    state_exp = classify_slick_evolution_state(prev_area_km2=10.0, curr_area_km2=12.5, match_iou=0.85)
    assert state_exp == "EXPANSION"

    # 25% area drop -> CONTRACTION
    state_cont = classify_slick_evolution_state(prev_area_km2=10.0, curr_area_km2=7.0, match_iou=0.80)
    assert state_cont == "CONTRACTION"

    # 5% change -> PERSISTENCE
    state_pers = classify_slick_evolution_state(prev_area_km2=10.0, curr_area_km2=10.4, match_iou=0.90)
    assert state_pers == "PERSISTENCE"


def test_kinematics_calculation():
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)  # 12 hours later

    res = calculate_kinematics(
        prev_lon=80.0, prev_lat=13.0, prev_time=t0,
        curr_lon=80.1, curr_lat=13.0, curr_time=t1,
        prev_area_km2=5.0, curr_area_km2=7.4
    )

    assert res["elapsed_hours"] == 12.0
    assert res["displacement_km"] > 9.0
    assert res["drift_speed_kmh"] > 0.5
    assert res["growth_rate_km2_per_hr"] == 0.20


def test_hungarian_association_matching():
    tracker = MultiTemporalSlickTracker(max_matching_distance_km=30.0)
    now = datetime.now(timezone.utc)
    
    existing_tracks = [
        {"track_id": "T1", "centroid_lon": 80.30, "centroid_lat": 13.20, "area_km2": 4.5, "last_seen": now}
    ]
    
    # Near detection (should match T1)
    new_detections = [
        {"detection_id": "D1", "centroid_lon": 80.32, "centroid_lat": 13.21, "area_km2": 4.8},
        # Distant detection (should form new track)
        {"detection_id": "D2", "centroid_lon": 81.50, "centroid_lat": 14.50, "area_km2": 2.0}
    ]

    assoc = tracker.associate_detections(existing_tracks, new_detections, observation_time=now + timedelta(hours=12))

    assert len(assoc["matched_pairs"]) == 1
    assert assoc["matched_pairs"][0]["track"]["track_id"] == "T1"
    assert assoc["matched_pairs"][0]["detection"]["detection_id"] == "D1"
    assert len(assoc["new_tracks"]) == 1
    assert assoc["new_tracks"][0]["detection_id"] == "D2"
