"""
Impact, Risk Assessment, and Decision Support Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.database.models import ImpactAssessment, RiskAssessment, ResponseRecommendation, TrackedSlick
from backend.app.schemas.impact import ImpactAssessmentResponse
from backend.app.schemas.risk import RiskAssessmentResponse, ResponseRecommendationResponse
from backend.app.schemas.common import APIResponse
from backend.app.risk.sensitivity import run_weight_sensitivity_analysis

router = APIRouter(tags=["Impact, Risk & Decision Support"])


@router.get("/impacts/{forecast_run_id}", response_model=APIResponse[List[ImpactAssessmentResponse]])
def get_impacts_for_forecast(forecast_run_id: str, db: Session = Depends(get_db)):
    impacts = db.query(ImpactAssessment).filter(ImpactAssessment.forecast_run_id == forecast_run_id).all()
    return APIResponse(data=impacts)


@router.get("/risk/{impact_id}", response_model=APIResponse[RiskAssessmentResponse])
def get_risk_assessment(impact_id: str, db: Session = Depends(get_db)):
    risk = db.query(RiskAssessment).filter(RiskAssessment.impact_assessment_id == impact_id).first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk assessment not found for impact")
    return APIResponse(data=risk)


@router.get("/recommendations/{track_id}", response_model=APIResponse[List[ResponseRecommendationResponse]])
def get_track_recommendations(track_id: str, db: Session = Depends(get_db)):
    recs = (
        db.query(ResponseRecommendation)
        .join(RiskAssessment)
        .join(ImpactAssessment)
        .join(ImpactAssessment.forecast_run)
        .filter(ImpactAssessment.forecast_run.has(track_id=track_id))
        .order_by(ResponseRecommendation.priority_rank.asc())
        .all()
    )
    return APIResponse(data=recs)


@router.get("/risk/analysis/sensitivity")
def get_risk_sensitivity_analysis(db: Session = Depends(get_db)):
    # Sample assessments for sensitivity verification
    samples = [
        {"impact_probability": 0.85, "sensitivity_weight": 4.8, "distance_to_slick_km": 4.2, "growth_rate_km2_hr": 0.12, "horizon_hours": 12, "asset_type": "protected_area", "asset_name": "Pulicat Sanctuary"},
        {"impact_probability": 0.65, "sensitivity_weight": 3.8, "distance_to_slick_km": 8.5, "growth_rate_km2_hr": 0.08, "horizon_hours": 24, "asset_type": "fishery", "asset_name": "Kattupalli Fishery"},
        {"impact_probability": 0.30, "sensitivity_weight": 2.2, "distance_to_slick_km": 14.0, "growth_rate_km2_hr": 0.00, "horizon_hours": 48, "asset_type": "port", "asset_name": "Kamarajar Port"}
    ]
    analysis = run_weight_sensitivity_analysis(samples, perturbation_pct=0.20)
    return APIResponse(data=analysis)
