"""
Response Decision Support and Monitoring Prioritization
Generates ranked decision-support guidance, boom deployment recommendations, and satellite retasking schedules.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List


class ResponsePrioritizer:
    """
    Translates risk assessments into operational decision-support recommendations.
    """
    @staticmethod
    def generate_recommendations(
        risk_assessments: List[Dict[str, Any]],
        track_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Ranks threatened assets and generates structured guidance.
        """
        # Sort by total risk score descending
        sorted_risks = sorted(risk_assessments, key=lambda r: r["total_risk_score"], reverse=True)
        recommendations = []

        rank = 1
        for r in sorted_risks:
            score = r["total_risk_score"]
            cat = r["risk_category"]
            asset_name = r.get("asset_name", "Coastal Zone")
            asset_type = r.get("asset_type", "general")
            time_window_h = r.get("earliest_time_to_impact_hours", 24.0)

            if cat in ["VERY_HIGH", "HIGH"]:
                if asset_type in ["protected_area", "wetland"]:
                    action_type = "CONTAINMENT_DEPLOYMENT"
                    guidance = (
                        f"Priority 1 Containment: Stage containment booms and absorbent barriers at {asset_name} "
                        f"inlet channels within next {round(time_window_h, 1)} hours."
                    )
                    reason = (
                        f"High ecological sensitivity ({asset_type}) with {round(r['factor_impact_probability'] * 100)}% "
                        f"forecast impact probability."
                    )
                elif asset_type == "fishery":
                    action_type = "FISHERY_NOTICE_AND_PROTECTION"
                    guidance = (
                        f"Issue precautionary marine exclusion advisory for {asset_name} fishing vessels; "
                        f"deploy deflection booms around aquaculture enclosures."
                    )
                    reason = f"Imminent slick trajectory threat (Estimated arrival: {round(time_window_h, 1)}h)."
                else:
                    action_type = "SHORELINE_DEFENSE"
                    guidance = f"Deploy shoreline protection teams and skimmer vessels near {asset_name}."
                    reason = f"High risk score ({score}/100) and coastal exposure."

            elif cat == "MODERATE":
                action_type = "AERIAL_VERIFICATION"
                guidance = (
                    f"Task maritime patrol aircraft or UAV for visual/thermal verification of slick plume leading edge "
                    f"towards {asset_name}."
                )
                reason = "Moderate risk; confirm thickness and emulsion state before heavy asset deployment."
            else:
                action_type = "ROUTINE_MONITORING"
                guidance = f"Maintain passive radar tracking for {asset_name} during next satellite pass."
                reason = "Low immediate threat; trajectory does not show significant intersection within 48h."

            recommendations.append({
                "priority_rank": rank,
                "risk_id": r.get("risk_id", f"risk-{rank}"),
                "asset_name": asset_name,
                "total_risk_score": score,
                "action_category": action_type,
                "recommendation_text": guidance,
                "reasoning": reason,
                "time_window_hours": round(time_window_h, 1),
                "analyst_review_status": "PENDING_REVIEW",
                "disclaimer": "DECISION SUPPORT ONLY: This recommendation is generated as advisory guidance and does not constitute an autonomous emergency command."
            })
            rank += 1

        return recommendations
