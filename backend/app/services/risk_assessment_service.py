"""
Risk Assessment Service

Transparent wrapper over ExplainableRiskEngine for API and incident context.
"""
from typing import Any, Dict, List
from backend.app.risk.engine import ExplainableRiskEngine


class RiskAssessmentService:
    def __init__(self):
        self.engine = ExplainableRiskEngine()

    def evaluate(
        self,
        impact_probability: float,
        asset_sensitivity_weight: float,
        distance_to_slick_km: float,
        slick_growth_rate_km2_hr: float,
        forecast_horizon_hours: int,
        asset_type: str,
        asset_name: str,
    ) -> Dict[str, Any]:
        return self.engine.evaluate_risk(
            impact_probability=impact_probability,
            asset_sensitivity_weight=asset_sensitivity_weight,
            distance_to_slick_km=distance_to_slick_km,
            slick_growth_rate_km2_hr=slick_growth_rate_km2_hr,
            forecast_horizon_hours=forecast_horizon_hours,
            asset_type=asset_type,
            asset_name=asset_name,
        )

    def explain(self, risk_result: Dict[str, Any]) -> str:
        return risk_result.get("explanation_text", "Risk explanation unavailable.")
