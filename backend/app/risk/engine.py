"""
Explainable Risk Engine
Computes transparent, factor-decomposed risk scores and structured natural-language explanations.
"""
from typing import Any, Dict, List, Optional
import numpy as np


# Standard Analytical Hierarchy Process (AHP) derived weights summing to 100
DEFAULT_RISK_WEIGHTS: Dict[str, float] = {
    "impact_probability": 0.28,      # w1: Likelihood of slick trajectory hitting asset
    "asset_sensitivity": 0.22,       # w2: Ecological / conservation importance (MPA/mangrove vs port)
    "proximity": 0.18,               # w3: Proximity decay from current slick edge
    "slick_expansion": 0.12,         # w4: Growth rate from temporal tracking
    "forecast_uncertainty": 0.10,    # w5: Penalty for wide dispersion / urgent need for monitoring
    "economic_exposure": 0.10        # w6: Fisheries / human population exposure
}


class ExplainableRiskEngine:
    """
    Computes inspectable risk scores decomposed into 6 distinct physical and environmental factors.
    """
    def __init__(self, weights: Optional[Dict[str, float]] = None, version_tag: str = "v1.0-AHP-standard"):
        self.weights = weights or DEFAULT_RISK_WEIGHTS
        self.version_tag = version_tag
        # Verify normalization
        total_w = sum(self.weights.values())
        if abs(total_w - 1.0) > 1e-4:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def evaluate_risk(
        self,
        impact_probability: float,        # [0.0 - 1.0]
        asset_sensitivity_weight: float,  # [1.0 - 5.0]
        distance_to_slick_km: float,      # km
        slick_growth_rate_km2_hr: float,  # km2/hr
        forecast_horizon_hours: int,      # 6, 12, 24, 48
        asset_type: str,
        asset_name: str
    ) -> Dict[str, Any]:
        """
        Calculates 6-factor decomposed risk score and generates a traceable explanation.
        """
        # 1. Normalized Impact Probability Term [0 - 1]
        t1_prob = float(np.clip(impact_probability, 0.0, 1.0))

        # 2. Normalized Asset Sensitivity Term [0 - 1]
        t2_sens = float(np.clip((asset_sensitivity_weight - 1.0) / 4.0, 0.0, 1.0))

        # 3. Normalized Proximity Term [0 - 1] (Exponential decay: 1.0 at 0km, ~0.13 at 20km)
        t3_prox = float(np.exp(-0.10 * max(distance_to_slick_km, 0.0)))

        # 4. Normalized Slick Expansion Rate [0 - 1] (0.0 for stable/shrinking, 1.0 for +1.0 km2/hr)
        t4_exp = float(np.clip(max(0.0, slick_growth_rate_km2_hr) / 0.50, 0.0, 1.0))

        # 5. Normalized Forecast Uncertainty / Urgency Penalty [0 - 1]
        # Longer lead times or fast-approaching slicks have higher monitoring urgency
        t5_uncert = float(np.clip(forecast_horizon_hours / 48.0, 0.1, 1.0))

        # 6. Normalized Economic / Coastal Exposure [0 - 1]
        economic_types = {"fishery": 0.85, "beach": 0.70, "coastal_population": 0.90, "port": 0.60, "protected_area": 0.95}
        t6_econ = economic_types.get(asset_type.lower(), 0.50)

        # Weighted Sum mapped to 0 - 100 Scale
        w = self.weights
        c1 = w["impact_probability"] * t1_prob
        c2 = w["asset_sensitivity"] * t2_sens
        c3 = w["proximity"] * t3_prox
        c4 = w["slick_expansion"] * t4_exp
        c5 = w["forecast_uncertainty"] * t5_uncert
        c6 = w["economic_exposure"] * t6_econ

        raw_score = (c1 + c2 + c3 + c4 + c5 + c6) * 100.0
        total_risk_score = round(float(np.clip(raw_score, 0.0, 100.0)), 1)

        # Categorize
        if total_risk_score >= 75.0:
            category = "VERY_HIGH"
        elif total_risk_score >= 50.0:
            category = "HIGH"
        elif total_risk_score >= 25.0:
            category = "MODERATE"
        else:
            category = "LOW"

        # Generate Explainable Justification
        reasons = []
        if t1_prob >= 0.70:
            reasons.append(f"high predicted trajectory impact probability ({round(t1_prob * 100)}%)")
        elif t1_prob >= 0.35:
            reasons.append(f"moderate impact probability ({round(t1_prob * 100)}%) within {forecast_horizon_hours}h horizon")

        if t2_sens >= 0.75:
            reasons.append(f"critical ecological sensitivity ({asset_type.replace('_', ' ').title()})")
        
        if distance_to_slick_km <= 8.0:
            reasons.append(f"close proximity ({distance_to_slick_km} km to active slick boundary)")

        if slick_growth_rate_km2_hr > 0.05:
            reasons.append(f"active slick expansion rate (+{round(slick_growth_rate_km2_hr, 3)} km²/hr)")

        explanation_prose = (
            f"Assessed as {category} RISK (Score: {total_risk_score}/100) for '{asset_name}'. "
            f"Key driving factors: {', '.join(reasons) if reasons else 'baseline exposure'}. "
            f"Evaluated under weight schema {self.version_tag}."
        )

        return {
            "total_risk_score": total_risk_score,
            "risk_category": category,
            "factor_impact_probability": round(t1_prob, 3),
            "factor_asset_sensitivity": round(t2_sens, 3),
            "factor_proximity": round(t3_prox, 3),
            "factor_slick_expansion": round(t4_exp, 3),
            "factor_forecast_uncertainty": round(t5_uncert, 3),
            "factor_economic_exposure": round(t6_econ, 3),
            "factor_breakdown": {
                "weights": self.weights,
                "normalized_terms": {
                    "impact_prob": round(t1_prob, 3),
                    "sensitivity": round(t2_sens, 3),
                    "proximity": round(t3_prox, 3),
                    "expansion": round(t4_exp, 3),
                    "uncertainty": round(t5_uncert, 3),
                    "economic": round(t6_econ, 3)
                },
                "weighted_contributions": {
                    "impact_prob_pts": round(c1 * 100.0, 2),
                    "sensitivity_pts": round(c2 * 100.0, 2),
                    "proximity_pts": round(c3 * 100.0, 2),
                    "expansion_pts": round(c4 * 100.0, 2),
                    "uncertainty_pts": round(c5 * 100.0, 2),
                    "economic_pts": round(c6 * 100.0, 2)
                }
            },
            "explanation_text": explanation_prose,
            "weight_config_version": self.version_tag
        }
