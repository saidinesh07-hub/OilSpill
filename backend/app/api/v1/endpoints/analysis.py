"""
Timeline and Incident Analysis Endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from backend.app.database.session import get_db
from backend.app.database.models import TrackedSlick, TemporalObservation
from backend.app.schemas.common import APIResponse
from backend.app.services.incident_context import IncidentContextBuilder
from backend.app.temporal.evolution import classify_evolution_state

router = APIRouter(prefix="/analysis", tags=["Timeline & Incident Analysis"])


@router.get("/incident")
def get_incident_context(
    track_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Structured incident state for assistant grounding and dashboard integration."""
    builder = IncidentContextBuilder(db=db)
    ctx = builder.build(track_id=track_id)
    return APIResponse(data=ctx.to_dict())


@router.get("/timeline/{track_id}")
def get_track_timeline(track_id: str, db: Session = Depends(get_db)):
    """
    Temporal intelligence for a tracked slick — area change, displacement, kinematics.
    """
    track = (
        db.query(TrackedSlick)
        .options(
            joinedload(TrackedSlick.temporal_observations).joinedload(TemporalObservation.detection)
        )
        .filter(TrackedSlick.track_id == track_id)
        .first()
    )
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    sorted_obs = sorted(track.temporal_observations, key=lambda t: t.observation_time)
    steps = []

    for idx, obs in enumerate(sorted_obs):
        step = {
            "step_index": idx,
            "observation_time": obs.observation_time.isoformat(),
            "area_km2": obs.area_km2,
            "area_delta_km2": obs.area_delta_km2,
            "centroid_displacement_m": obs.centroid_displacement_m,
            "observed_state": obs.observed_state,
            "detection_id": obs.detection_id,
            "detection": None,
        }
        if obs.detection:
            d = obs.detection
            step["detection"] = {
                "detection_id": d.detection_id,
                "geom_geojson": d.geom_geojson,
                "centroid_lat": d.centroid_lat,
                "centroid_lon": d.centroid_lon,
                "area_km2": d.area_km2,
                "predicted_class": d.predicted_class,
                "confidence": d.confidence,
                "lookalike_risk_score": d.lookalike_risk_score,
                "model_version": d.model_version,
                "morphology_features": d.morphology_features,
            }
        steps.append(step)

    summary = {
        "track_id": track.track_id,
        "slick_name": track.slick_name,
        "pass_count": len(steps),
        "current_drift_speed_kmh": track.drift_speed_kmh,
        "current_drift_heading_deg": track.drift_heading_deg,
        "current_growth_rate_km2_per_hr": track.growth_rate_km2_per_hr,
        "total_area_change_km2": sum(s["area_delta_km2"] for s in steps),
    }

    return APIResponse(data={"summary": summary, "steps": steps})


@router.get("/timeline/{track_id}/step/{step_index}")
def get_timeline_step(track_id: str, step_index: int, db: Session = Depends(get_db)):
    """Return state for a single temporal pass — used by dashboard scrubber."""
    timeline = get_track_timeline(track_id, db)
    steps = timeline.data["steps"]  # type: ignore
    if step_index < 0 or step_index >= len(steps):
        raise HTTPException(status_code=404, detail="Timeline step not found")
    return APIResponse(data=steps[step_index])
