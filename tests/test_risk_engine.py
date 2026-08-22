"""
Unit Tests for Explainable Risk Engine and Sensitivity Analysis
"""
import pytest
from backend.app.risk.engine import ExplainableRiskEngine
from backend.app.risk.sensitivity import run_weight_sensitivity_analysis


def test_explainable_risk_scoring():
    engine = ExplainableRiskEngine()
    
    # Critical threat case (MPA, 5km away, 85% probability, rapid expansion)
    high_threat = engine.evaluate_risk(
        impact_probability=0.85,
        asset_sensitivity_weight=4.8,
        distance_to_slick_km=5.0,
        slick_growth_rate_km2_hr=0.25,
        forecast_horizon_hours=12,
        asset_type="protected_area",
        asset_name="Pulicat Reserve"
    )

    assert high_threat["total_risk_score"] >= 65.0
    assert high_threat["risk_category"] in ["HIGH", "VERY_HIGH"]
    assert "Pulicat Reserve" in high_threat["explanation_text"]
    assert "factor_breakdown" in high_threat

    # Minor distant threat case (Port, 30km away, 10% probability, no expansion)
    low_threat = engine.evaluate_risk(
        impact_probability=0.10,
        asset_sensitivity_weight=2.0,
        distance_to_slick_km=30.0,
        slick_growth_rate_km2_hr=0.0,
        forecast_horizon_hours=48,
        asset_type="port",
        asset_name="Commercial Anchorage"
    )

    assert low_threat["total_risk_score"] < 40.0
    assert low_threat["total_risk_score"] < high_threat["total_risk_score"]


def test_sensitivity_monotonicity():
    samples = [
        {"impact_probability": 0.8, "sensitivity_weight": 4.5, "distance_to_slick_km": 4.0, "asset_type": "protected_area", "asset_name": "A1"},
        {"impact_probability": 0.3, "sensitivity_weight": 2.0, "distance_to_slick_km": 20.0, "asset_type": "port", "asset_name": "A2"}
    ]
    sens = run_weight_sensitivity_analysis(samples, perturbation_pct=0.20)
    assert sens["overall_stability"] == "ROBUST_AND_MONOTONIC"
