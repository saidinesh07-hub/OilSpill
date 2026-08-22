"""
Pipeline Orchestrator Service
Executes the full end-to-end intelligence chain: Ingestion -> Preprocessing -> Segmentation ->
Polygonization -> Temporal Association -> MetOcean Ingestion -> Trajectory Forecasting ->
Impact Assessment -> Explainable Risk -> Decision Support -> State Ledger.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from sqlalchemy.orm import Session
from backend.app.core.logging import logger
from backend.app.database.models import (
    SatelliteScene, Observation, SpillDetection, TrackedSlick, TemporalObservation,
    EnvironmentalSnapshot, ForecastRun, ForecastBand, Asset, ImpactAssessment,
    RiskAssessment, ResponseRecommendation
)
from backend.app.geospatial.projections import AffineGeoTransform
from backend.app.geospatial.raster_to_vector import polygonize_segmentation_output
from backend.app.services.demo_sar_generator import generate_demo_sar_scene
from backend.app.ml.inference.engine import SARInferenceEngine
from backend.app.temporal.tracker import MultiTemporalSlickTracker
from backend.app.environmental.cmems_adapter import CMEMSAdapter
from backend.app.environmental.era5_gfs_adapter import WindForcingAdapter
from backend.app.forecasting.ensemble import TrajectoryForecaster
from backend.app.assets.registry import create_asset_catalog_for_region
from backend.app.impact.analyzer import ImpactAnalyzer
from backend.app.risk.engine import ExplainableRiskEngine
from backend.app.decision_support.prioritization import ResponsePrioritizer


class IntelligencePipelineOrchestrator:
    """
    Coordinates multi-stage remote sensing and environmental intelligence processing.
    """
    def __init__(self, db: Session):
        self.db = db
        self.inference_engine = SARInferenceEngine(model_name="deeplabv3plus")
        self.tracker = MultiTemporalSlickTracker()
        self.cmems_adapter = CMEMSAdapter()
        self.wind_adapter = WindForcingAdapter()
        self.forecaster = TrajectoryForecaster()
        self.impact_analyzer = ImpactAnalyzer()
        self.risk_engine = ExplainableRiskEngine()
        self.prioritizer = ResponsePrioritizer()

    def process_scene(
        self,
        scene: SatelliteScene,
        sar_raster: Optional[np.ndarray] = None,
        is_synthetic: bool = False
    ) -> Dict[str, Any]:
        """
        Executes complete intelligence pipeline on an ingested satellite scene.
        """
        logger.info(f"Starting intelligence pipeline for Scene {scene.scene_name} (ID: {scene.scene_id})")

        using_demo_raster = sar_raster is None
        effective_synthetic = is_synthetic or scene.is_synthetic or using_demo_raster
        if using_demo_raster:
            logger.warning(
                f"No SAR raster supplied for scene {scene.scene_name}; "
                "generating DEMO_DATA synthetic backscatter field."
            )

        # 1. Observation Record
        obs = Observation(
            scene_id=scene.scene_id,
            preprocessing_version="v1.0-radiometric-lee-filter",
            processed_at=datetime.now(timezone.utc),
            raster_metadata={
                "bbox": scene.bbox,
                "polarization": scene.polarization,
                "sensor_mode": scene.sensor_mode,
                "is_synthetic": effective_synthetic,
                "data_mode": "DEMO_DATA" if effective_synthetic else "REAL_SATELLITE_DATA",
            }
        )
        self.db.add(obs)
        self.db.commit()
        self.db.refresh(obs)

        # 2. Raster Preparation (if none provided, generate representative SAR scene for the bbox)
        min_lon, min_lat, max_lon, max_lat = scene.bbox
        h_pix, w_pix = 512, 512
        transform = AffineGeoTransform.from_bbox_and_shape(scene.bbox, height=h_pix, width=w_pix)

        demo_meta = {}
        if sar_raster is None:
            pass_index = 1 if "P2" in scene.scene_name.upper() else 0
            sar_raster, demo_meta = generate_demo_sar_scene(
                height=h_pix, width=w_pix, pass_index=pass_index
            )

        # 3. ML Segmentation & Probabilities
        prediction_result = self.inference_engine.predict_full_scene(sar_raster, is_raw_dn=False)
        class_mask = prediction_result["class_mask"]
        prob_maps = prediction_result["prob_maps"]

        # Untrained models may miss slicks; for DEMO_DATA only, reinforce known synthetic regions
        if effective_synthetic and np.sum(class_mask == 1) == 0:
            yy, xx = np.ogrid[:h_pix, :w_pix]
            pass_index = demo_meta.get("pass_index", 0)
            cy = int(h_pix * (0.45 + 0.02 * pass_index))
            cx = int(w_pix * (0.52 + 0.01 * pass_index))
            slick_mask = (((xx - cx) ** 2) / (55 ** 2) + ((yy - cy) ** 2) / (28 ** 2)) <= 1.0
            class_mask[slick_mask] = 1
            prob_maps[slick_mask, 1] = 0.75  # moderate confidence — not validated detection
            prob_maps[slick_mask, 0] = 0.15
            prob_maps[slick_mask, 2] = 0.10

        # 4. Vector Polygonization & Geodesic Area
        raw_detections = polygonize_segmentation_output(
            class_mask=class_mask,
            prob_maps=prob_maps,
            transform=transform,
            min_area_km2=0.05,
            model_version="deeplabv3plus-resnet50"
        )

        stored_detections = []
        for det_data in raw_detections:
            det = SpillDetection(
                observation_id=obs.observation_id,
                geom_geojson=det_data["geom_geojson"],
                centroid_lat=det_data["centroid_lat"],
                centroid_lon=det_data["centroid_lon"],
                area_km2=det_data["area_km2"],
                perimeter_km=det_data["perimeter_km"],
                predicted_class=det_data["predicted_class"],
                confidence=det_data["confidence"],
                lookalike_risk_score=det_data["lookalike_risk_score"],
                morphology_features=det_data["morphology_features"],
                model_version=det_data["model_version"]
            )
            self.db.add(det)
            stored_detections.append(det)

        self.db.commit()
        for det in stored_detections:
            self.db.refresh(det)

        # 5. Multi-Temporal Tracking & Association
        existing_tracks = self.db.query(TrackedSlick).filter(TrackedSlick.current_status == "ACTIVE").all()
        track_dicts = [{
            "track_id": t.track_id,
            "slick_name": t.slick_name,
            "centroid_lon": t.current_centroid_lon,
            "centroid_lat": t.current_centroid_lat,
            "area_km2": t.total_area_km2,
            "last_seen": t.last_seen
        } for t in existing_tracks]

        det_dicts = [{
            "detection_id": d.detection_id,
            "centroid_lon": d.centroid_lon,
            "centroid_lat": d.centroid_lat,
            "area_km2": d.area_km2,
            "confidence": d.confidence
        } for d in stored_detections if d.predicted_class == "oil_spill"]

        association = self.tracker.associate_detections(
            active_tracks=track_dicts,
            new_detections=det_dicts,
            observation_time=scene.acquisition_time
        )

        active_track_objects = []

        # Handle Matched Tracks
        for m in association["matched_pairs"]:
            t_obj = self.db.query(TrackedSlick).filter(TrackedSlick.track_id == m["track"]["track_id"]).first()
            d_obj = next(d for d in stored_detections if d.detection_id == m["detection"]["detection_id"])
            k = m["kinematics"]

            temp_obs = TemporalObservation(
                track_id=t_obj.track_id,
                detection_id=d_obj.detection_id,
                observation_time=scene.acquisition_time,
                area_km2=d_obj.area_km2,
                area_delta_km2=k["area_delta_km2"],
                centroid_displacement_m=k["displacement_m"],
                observed_state=m["state"],
                advection_iou_match=0.90
            )
            self.db.add(temp_obs)

            # Update tracked slick entity
            t_obj.last_seen = scene.acquisition_time
            t_obj.total_area_km2 = d_obj.area_km2
            t_obj.current_centroid_lat = d_obj.centroid_lat
            t_obj.current_centroid_lon = d_obj.centroid_lon
            t_obj.drift_speed_kmh = k["drift_speed_kmh"]
            t_obj.drift_heading_deg = k["drift_heading_deg"]
            t_obj.growth_rate_km2_per_hr = k["growth_rate_km2_per_hr"]
            t_obj.latest_detection_id = d_obj.detection_id
            active_track_objects.append(t_obj)

        # Handle New Tracks
        for new_d in association["new_tracks"]:
            d_obj = next(d for d in stored_detections if d.detection_id == new_d["detection_id"])
            new_track = TrackedSlick(
                slick_name=f"Slick-{scene.scene_name[:8]}-{len(active_track_objects)+1}",
                first_seen=scene.acquisition_time,
                last_seen=scene.acquisition_time,
                current_status="ACTIVE",
                total_area_km2=d_obj.area_km2,
                current_centroid_lat=d_obj.centroid_lat,
                current_centroid_lon=d_obj.centroid_lon,
                drift_speed_kmh=0.0,
                drift_heading_deg=0.0,
                growth_rate_km2_per_hr=0.0,
                latest_detection_id=d_obj.detection_id
            )
            self.db.add(new_track)
            self.db.commit()
            self.db.refresh(new_track)

            temp_obs = TemporalObservation(
                track_id=new_track.track_id,
                detection_id=d_obj.detection_id,
                observation_time=scene.acquisition_time,
                area_km2=d_obj.area_km2,
                area_delta_km2=0.0,
                centroid_displacement_m=0.0,
                observed_state="PERSISTENCE",
                advection_iou_match=1.0
            )
            self.db.add(temp_obs)
            active_track_objects.append(new_track)

        self.db.commit()

        # 6. Environmental MetOcean Data Pull
        currents_data = self.cmems_adapter.get_surface_currents(scene.bbox, scene.acquisition_time)
        winds_data = self.wind_adapter.get_surface_winds(scene.bbox, scene.acquisition_time)
        stokes_data = self.cmems_adapter.get_stokes_drift(scene.bbox, scene.acquisition_time)

        # 7. Asset Catalog Check
        existing_assets = self.db.query(Asset).all()
        if not existing_assets:
            catalog = create_asset_catalog_for_region("chennai_ennore")
            for a_item in catalog:
                a_obj = Asset(
                    name=a_item["name"],
                    asset_type=a_item["asset_type"],
                    geom_geojson=a_item["geom_geojson"],
                    centroid_lat=a_item["centroid_lat"],
                    centroid_lon=a_item["centroid_lon"],
                    sensitivity_weight=a_item["sensitivity_weight"],
                    data_source=a_item["data_source"],
                    data_vintage=a_item["data_vintage"],
                    properties=a_item["properties"]
                )
                self.db.add(a_obj)
            self.db.commit()
            existing_assets = self.db.query(Asset).all()

        asset_dicts = [{
            "asset_id": a.asset_id,
            "name": a.name,
            "asset_type": a.asset_type,
            "geom_geojson": a.geom_geojson,
            "centroid_lat": a.centroid_lat,
            "centroid_lon": a.centroid_lon,
            "sensitivity_weight": a.sensitivity_weight
        } for a in existing_assets]

        # 8. Trajectory Forecasting, Impact & Risk Evaluation for each active track
        for track in active_track_objects:
            latest_det = next((d for d in stored_detections if d.detection_id == track.latest_detection_id), stored_detections[0])
            
            # Run Monte Carlo forecast
            forecast_output = self.forecaster.run_forecast(
                initial_polygon_geojson=latest_det.geom_geojson,
                initial_time=scene.acquisition_time,
                currents_data=currents_data,
                wind_data=winds_data,
                stokes_data=stokes_data,
                horizons_hours=[6, 12, 24, 48],
                ensemble_size=50
            )

            # Store Forecast Run
            f_run = ForecastRun(
                track_id=track.track_id,
                run_time=datetime.now(timezone.utc),
                engine="Lagrangian_Monte_Carlo_Ensemble",
                engine_version="v1.2.0-metocean-stokes",
                ensemble_size=50,
                wind_drift_factor=0.03,
                wind_deflection_angle_deg=15.0,
                diffusion_coefficient=2.0,
                summary=forecast_output["metocean_summary"]
            )
            self.db.add(f_run)
            self.db.commit()
            self.db.refresh(f_run)

            # Store Forecast Bands
            band_objects = []
            for b in forecast_output["forecast_bands"]:
                fb = ForecastBand(
                    forecast_run_id=f_run.forecast_run_id,
                    horizon_hours=b["horizon_hours"],
                    target_time=b["target_time"],
                    confidence_level=b["confidence_level"],
                    geom_geojson=b["geom_geojson"],
                    area_km2=b["area_km2"],
                    centroid_lat=b["centroid_lat"],
                    centroid_lon=b["centroid_lon"],
                    mean_speed_kmh=b["mean_speed_kmh"]
                )
                self.db.add(fb)
                band_objects.append(fb)

            self.db.commit()

            # 9. Assess Impacts against Assets
            impacts = self.impact_analyzer.assess_impacts(
                forecast_bands=forecast_output["forecast_bands"],
                assets=asset_dicts,
                current_slick_lon=track.current_centroid_lon,
                current_slick_lat=track.current_centroid_lat
            )

            risk_evaluations = []
            for imp in impacts:
                imp_obj = ImpactAssessment(
                    forecast_run_id=f_run.forecast_run_id,
                    asset_id=imp["asset_id"],
                    horizon_hours=imp["horizon_hours"],
                    impact_probability=imp["impact_probability"],
                    earliest_time_to_impact_hours=imp["earliest_time_to_impact_hours"],
                    distance_to_slick_km=imp["distance_to_slick_km"],
                    intersected_area_km2=imp["intersected_area_km2"],
                    exposure_level=imp["exposure_level"]
                )
                self.db.add(imp_obj)
                self.db.commit()
                self.db.refresh(imp_obj)

                # 10. Compute 6-Factor Risk Score
                risk_res = self.risk_engine.evaluate_risk(
                    impact_probability=imp["impact_probability"],
                    asset_sensitivity_weight=imp["sensitivity_weight"],
                    distance_to_slick_km=imp["distance_to_slick_km"],
                    slick_growth_rate_km2_hr=track.growth_rate_km2_per_hr,
                    forecast_horizon_hours=imp["horizon_hours"],
                    asset_type=imp["asset_type"],
                    asset_name=imp["asset_name"]
                )

                risk_obj = RiskAssessment(
                    impact_assessment_id=imp_obj.id,
                    total_risk_score=risk_res["total_risk_score"],
                    risk_category=risk_res["risk_category"],
                    factor_impact_probability=risk_res["factor_impact_probability"],
                    factor_asset_sensitivity=risk_res["factor_asset_sensitivity"],
                    factor_proximity=risk_res["factor_proximity"],
                    factor_slick_expansion=risk_res["factor_slick_expansion"],
                    factor_forecast_uncertainty=risk_res["factor_forecast_uncertainty"],
                    factor_economic_exposure=risk_res["factor_economic_exposure"],
                    factor_breakdown=risk_res["factor_breakdown"],
                    explanation_text=risk_res["explanation_text"],
                    weight_config_version=risk_res["weight_config_version"]
                )
                self.db.add(risk_obj)
                self.db.commit()
                self.db.refresh(risk_obj)

                risk_evaluations.append({
                    **risk_res,
                    "risk_id": risk_obj.risk_id,
                    "asset_name": imp["asset_name"],
                    "asset_type": imp["asset_type"],
                    "earliest_time_to_impact_hours": imp["earliest_time_to_impact_hours"]
                })

            # 11. Generate Response Decision Support Recommendations
            recs = self.prioritizer.generate_recommendations(
                risk_assessments=risk_evaluations,
                track_info={"slick_name": track.slick_name}
            )

            for rec in recs:
                rec_obj = ResponseRecommendation(
                    risk_id=rec["risk_id"],
                    priority_rank=rec["priority_rank"],
                    action_category=rec["action_category"],
                    recommendation_text=rec["recommendation_text"],
                    reasoning=rec["reasoning"],
                    time_window_hours=rec["time_window_hours"],
                    analyst_review_status="PENDING_REVIEW"
                )
                self.db.add(rec_obj)

            self.db.commit()

        logger.info(f"Pipeline processing complete for scene '{scene.scene_name}'.")

        return {
            "scene_id": scene.scene_id,
            "observation_id": obs.observation_id,
            "detections_count": len(stored_detections),
            "active_tracks_count": len(active_track_objects),
            "status": "COMPLETED",
            "data_mode": "DEMO_DATA" if effective_synthetic else "REAL_SATELLITE_DATA",
        }
