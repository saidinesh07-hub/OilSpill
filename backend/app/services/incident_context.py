"""
Incident Context Builder

Assembles structured application state for grounded assistant and analysis endpoints.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from backend.app.core.config import settings
from backend.app.database.models import (
    TrackedSlick, TemporalObservation, ForecastRun, ImpactAssessment,
    RiskAssessment, SpillDetection, SatelliteScene, Observation
)
from backend.app.schemas.data_contract import DataStatus


class IncidentContext:
    """Structured incident state for assistant grounding and API responses."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def to_dict(self) -> Dict[str, Any]:
        return self._data

    @property
    def track_id(self) -> Optional[str]:
        return self._data.get("track_id")

    @property
    def data_status(self) -> str:
        return self._data.get("data_status", DataStatus.UNAVAILABLE.value)


class IncidentContextBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build(self, track_id: Optional[str] = None) -> IncidentContext:
        track = self._get_track(track_id)
        if not track:
            return IncidentContext({
                "data_status": DataStatus.UNAVAILABLE.value,
                "message": "No active tracked slick found.",
            })

        latest_forecast = (
            self.db.query(ForecastRun)
            .filter(ForecastRun.track_id == track.track_id)
            .order_by(ForecastRun.run_time.desc())
            .first()
        )

        impacts: List[ImpactAssessment] = []
        if latest_forecast:
            impacts = (
                self.db.query(ImpactAssessment)
                .filter(ImpactAssessment.forecast_run_id == latest_forecast.forecast_run_id)
                .all()
            )

        top_impact = max(
            impacts,
            key=lambda i: i.risk_assessment.total_risk_score if i.risk_assessment else 0,
            default=None,
        )

        latest_det = None
        if track.latest_detection_id:
            latest_det = self.db.query(SpillDetection).filter(
                SpillDetection.detection_id == track.latest_detection_id
            ).first()

        temporal = sorted(track.temporal_observations, key=lambda t: t.observation_time)
        scene_data_status = DataStatus.DEMO.value
        if temporal and temporal[-1].detection:
            obs = self.db.query(Observation).filter(
                Observation.observation_id == temporal[-1].detection.observation_id
            ).first()
            if obs and obs.raster_metadata:
                scene_data_status = obs.raster_metadata.get("data_mode", DataStatus.DEMO.value)

        context = {
            "track_id": track.track_id,
            "slick_name": track.slick_name,
            "data_status": scene_data_status,
            "data_mode": settings.DATA_MODE,
            "current_observation": {
                "area_km2": track.total_area_km2,
                "centroid_lat": track.current_centroid_lat,
                "centroid_lon": track.current_centroid_lon,
                "drift_speed_kmh": track.drift_speed_kmh,
                "drift_heading_deg": track.drift_heading_deg,
                "growth_rate_km2_per_hr": track.growth_rate_km2_per_hr,
                "last_seen": track.last_seen.isoformat() if track.last_seen else None,
                "confidence": latest_det.confidence if latest_det else None,
                "predicted_class": latest_det.predicted_class if latest_det else None,
                "lookalike_risk_score": latest_det.lookalike_risk_score if latest_det else None,
                "model_version": latest_det.model_version if latest_det else None,
            },
            "historical_observations": [
                {
                    "observation_time": t.observation_time.isoformat(),
                    "area_km2": t.area_km2,
                    "area_delta_km2": t.area_delta_km2,
                    "centroid_displacement_m": t.centroid_displacement_m,
                    "observed_state": t.observed_state,
                    "detection_id": t.detection_id,
                }
                for t in temporal
            ],
            "forecast": None,
            "risk": None,
            "affected_assets": [],
            "confidence": latest_det.confidence if latest_det else None,
            "data_provenance": {
                "pipeline_mode": settings.DATA_MODE,
                "scene_data_status": scene_data_status,
            },
        }

        if latest_forecast:
            context["forecast"] = {
                "forecast_run_id": latest_forecast.forecast_run_id,
                "engine": latest_forecast.engine,
                "engine_version": latest_forecast.engine_version,
                "ensemble_size": latest_forecast.ensemble_size,
                "summary": latest_forecast.summary or {},
                "horizons_available": sorted({b.horizon_hours for b in latest_forecast.bands}),
                "uncertainty_note": "Probabilistic forecast — not a guaranteed future position.",
            }

        if top_impact and top_impact.risk_assessment:
            risk = top_impact.risk_assessment
            asset = top_impact.asset
            context["risk"] = {
                "risk_id": risk.risk_id,
                "total_risk_score": risk.total_risk_score,
                "risk_category": risk.risk_category,
                "factor_breakdown": risk.factor_breakdown,
                "explanation_text": risk.explanation_text,
            }
            context["most_affected_asset"] = asset.name if asset else None

        context["affected_assets"] = sorted(
            [
                {
                    "asset_id": imp.asset_id,
                    "asset_name": imp.asset.name if imp.asset else "Unknown",
                    "impact_probability": imp.impact_probability,
                    "earliest_time_to_impact_hours": imp.earliest_time_to_impact_hours,
                    "distance_to_slick_km": imp.distance_to_slick_km,
                    "exposure_level": imp.exposure_level,
                    "impact_type": "PREDICTED_POTENTIAL",
                }
                for imp in impacts
            ],
            key=lambda x: x["impact_probability"],
            reverse=True,
        )

        return IncidentContext(context)

    def _get_track(self, track_id: Optional[str]) -> Optional[TrackedSlick]:
        query = self.db.query(TrackedSlick).options(
            joinedload(TrackedSlick.temporal_observations).joinedload(TemporalObservation.detection)
        )
        if track_id:
            return query.filter(TrackedSlick.track_id == track_id).first()
        return query.order_by(TrackedSlick.last_seen.desc()).first()
