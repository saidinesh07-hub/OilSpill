from sqlalchemy.orm import Session
from datetime import datetime, timezone
import math
from fastapi import HTTPException

from backend.app.schemas.common import APIResponse

class IntelligenceOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        
    def get_unified_intelligence(self, spill_id: str):
        # Fallback to DEMO if requested demo
        if spill_id.startswith("DEMO"):
            from backend.app.api.v1.endpoints.incidents import _demo_payload
            demo_data = _demo_payload(13.23, 80.33, "Ennore Port (DEMO)")
            return APIResponse(data=demo_data)
            
        from backend.app.database.models import SpillDetection
        detection = self.db.query(SpillDetection).filter(SpillDetection.detection_id == spill_id).first()
        if not detection:
            raise HTTPException(status_code=404, detail="Spill detection not found")
            
        scene_time = detection.created_at.isoformat() if detection.created_at else datetime.now(timezone.utc).isoformat()
        spill_geom = detection.geom_geojson
        spill_lat = detection.centroid_lat
        spill_lon = detection.centroid_lon
        spill_area = detection.area_km2
        
        # Bounding box logic
        search_radius_km = 40.0
        lat_margin = search_radius_km / 111.0
        try:
            lon_margin = search_radius_km / (111.0 * math.cos(math.radians(spill_lat)))
        except Exception:
            lon_margin = lat_margin
            
        bbox = [spill_lon - lon_margin, spill_lat - lat_margin, spill_lon + lon_margin, spill_lat + lat_margin]

        # Vessel Correlation
        from backend.app.api.v1.endpoints.maritime import correlate_spill_vessels
        try:
            vessels_resp = correlate_spill_vessels(spill_id=spill_id, db=self.db)
            candidates = vessels_resp.data.get("candidates", [])
        except Exception as e:
            print(f"Failed to correlate vessels: {e}")
            candidates = []
            
        forecast_bands = []
        assets = []
        impacts = []
        recommendations = []
        active_track = None
        warnings = []

        try:
            from backend.app.forecasting.ensemble import TrajectoryForecaster
            from backend.app.environmental.cmems_adapter import CMEMSAdapter
            from backend.app.environmental.era5_gfs_adapter import WindForcingAdapter
            from backend.app.assets.registry import create_asset_catalog_for_region
            from backend.app.impact.analyzer import ImpactAnalyzer
            from backend.app.risk.engine import ExplainableRiskEngine
            from backend.app.decision_support.prioritization import ResponsePrioritizer
            
            forecaster = TrajectoryForecaster()
            cmems = CMEMSAdapter()
            wind = WindForcingAdapter()
            
            target_time_dt = datetime.fromisoformat(scene_time.replace("Z", "+00:00"))
            currents_data = cmems.get_surface_currents(bbox, target_time_dt)
            winds_data = wind.get_surface_winds(bbox, target_time_dt)
            stokes_data = cmems.get_stokes_drift(bbox, target_time_dt)
            
            env_provenance = {
                "currents": {
                    "source": currents_data.get("source", "Unknown"),
                    "data_mode": currents_data.get("data_mode", "UNKNOWN"),
                    "data_provenance": currents_data.get("data_provenance", "Unknown"),
                    "data_vintage": currents_data.get("data_vintage", datetime.now(timezone.utc).isoformat())
                },
                "winds": {
                    "source": winds_data.get("source", "Unknown"),
                    "data_mode": winds_data.get("data_mode", "UNKNOWN"),
                    "data_provenance": winds_data.get("data_provenance", "Unknown"),
                    "data_vintage": winds_data.get("data_vintage", datetime.now(timezone.utc).isoformat())
                }
            }
            
            forecast_output = forecaster.run_forecast(
                initial_polygon_geojson=spill_geom,
                initial_time=datetime.fromisoformat(scene_time.replace("Z", "+00:00")),
                currents_data=currents_data,
                wind_data=winds_data,
                stokes_data=stokes_data,
                horizons_hours=[6, 12, 24, 48],
                ensemble_size=50
            )
            
            forecast_bands = forecast_output["forecast_bands"]
            for b in forecast_bands:
                b["forecast_run_id"] = "real-run-1"
                b["id"] = f"real-band-{b['horizon_hours']}-{b['confidence_level']}"
                
            active_track = {
                "track_id": "real-track-1",
                "slick_name": f"REAL SLICK {spill_id[:6]}",
                "current_status": "ACTIVE",
                "total_area_km2": spill_area,
                "current_centroid_lat": spill_lat,
                "current_centroid_lon": spill_lon,
                "drift_speed_kmh": 0.0,
                "drift_heading_deg": 0.0,
                "temporal_observations": [
                    {
                        "observation_time": scene_time,
                        "area_km2": spill_area,
                        "observed_state": "PERSISTENCE",
                        "detection": {
                            "centroid_lat": spill_lat,
                            "centroid_lon": spill_lon,
                        }
                    }
                ]
            }
            
            catalog = create_asset_catalog_for_region("chennai_ennore")
            for a_item in catalog:
                assets.append({
                    "asset_id": f"real-asset-{len(assets)}",
                    "name": a_item["name"],
                    "asset_type": a_item["asset_type"],
                    "geom_geojson": a_item["geom_geojson"],
                    "centroid_lat": a_item["centroid_lat"],
                    "centroid_lon": a_item["centroid_lon"],
                    "sensitivity_weight": a_item["sensitivity_weight"],
                    "data_source": a_item["data_source"],
                    "data_vintage": a_item["data_vintage"],
                    "properties": a_item["properties"]
                })
                
            analyzer = ImpactAnalyzer()
            imp_res = analyzer.assess_impacts(
                forecast_bands=forecast_bands,
                assets=assets,
                current_slick_lon=spill_lon,
                current_slick_lat=spill_lat
            )
            
            risk_engine = ExplainableRiskEngine()
            risk_evaluations = []
            for i, imp in enumerate(imp_res):
                risk_res = risk_engine.evaluate_risk(
                    impact_probability=imp["impact_probability"],
                    asset_sensitivity_weight=imp["sensitivity_weight"],
                    distance_to_slick_km=imp["distance_to_slick_km"],
                    slick_growth_rate_km2_hr=0.0,
                    forecast_horizon_hours=imp["horizon_hours"],
                    asset_type=imp["asset_type"],
                    asset_name=imp["asset_name"]
                )
                imp["id"] = f"real-impact-{i}"
                imp["forecast_run_id"] = "real-run-1"
                imp["asset"] = next(a for a in assets if a["asset_id"] == imp["asset_id"])
                impacts.append(imp)
                
                risk_evaluations.append({
                    **risk_res,
                    "risk_id": f"real-risk-{i}",
                    "asset_name": imp["asset_name"],
                    "asset_type": imp["asset_type"],
                    "earliest_time_to_impact_hours": imp["earliest_time_to_impact_hours"]
                })
                
            prioritizer = ResponsePrioritizer()
            recs = prioritizer.generate_recommendations(
                risk_assessments=risk_evaluations,
                track_info={"slick_name": f"REAL SLICK {spill_id[:6]}"}
            )
            
            for i, rec in enumerate(recs):
                rec["id"] = f"real-rec-{i}"
                recommendations.append(rec)
                
        except Exception as e:
            warnings.append(f"Unified Intelligence Generation failed: {e}")
            
        return APIResponse(data={
            "spill_id": spill_id,
            "mode": "REAL",
            "candidates": candidates,
            "forecast_bands": forecast_bands,
            "active_track": active_track,
            "assets": assets,
            "impacts": impacts,
            "recommendations": recommendations,
            "environmental_provenance": env_provenance if 'env_provenance' in locals() else None,
            "warnings": warnings,
            "stage_status": {
                "forecasting": "OK" if forecast_bands else "ERROR"
            }
        })
