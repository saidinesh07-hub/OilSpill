"""
Explainable Risk Engine and Recommendation Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.impact import ImpactAssessmentResponse


class FactorBreakdown(BaseModel):
    impact_probability: float
    asset_sensitivity: float
    proximity: float
    slick_expansion: float
    forecast_uncertainty: float
    economic_exposure: float
    weights_applied: Dict[str, float]
    normalized_terms: Dict[str, float]


class ResponseRecommendationResponse(BaseModel):
    id: str
    risk_id: str
    priority_rank: int
    action_category: str
    recommendation_text: str
    reasoning: str
    time_window_hours: float
    target_geom_geojson: Optional[Dict[str, Any]] = None
    analyst_review_status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentResponse(BaseModel):
    risk_id: str
    impact_assessment_id: str
    total_risk_score: float
    risk_category: str  # "VERY_HIGH", "HIGH", "MODERATE", "LOW"
    factor_impact_probability: float
    factor_asset_sensitivity: float
    factor_proximity: float
    factor_slick_expansion: float
    factor_forecast_uncertainty: float
    factor_economic_exposure: float
    factor_breakdown: Dict[str, Any]
    explanation_text: str
    weight_config_version: str
    calculated_at: datetime
    impact: Optional[ImpactAssessmentResponse] = None
    recommendations: List[ResponseRecommendationResponse] = []
    model_config = ConfigDict(from_attributes=True)
