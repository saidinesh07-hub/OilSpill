"""
Monte Carlo Ensemble Trajectory Forecaster
Simulates multi-horizon trajectory ensembles (6h, 12h, 24h, 48h) under metocean forcing uncertainty.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from shapely.geometry import shape
from backend.app.core.logging import logger
from backend.app.forecasting.lagrangian import LagrangianAdvectionEngine
from backend.app.forecasting.contours import compute_containment_contours_for_particles
from backend.app.geospatial.geometry_ops import get_geodesic_distance_km


class TrajectoryForecaster:
    """
    Simulates probabilistic trajectory evolution and containment envelopes.
    """
    def __init__(
        self,
        wind_drift_factor: float = 0.03,
        wind_deflection_angle_deg: float = 15.0,
        diffusion_coefficient: float = 2.0
    ):
        self.advection_engine = LagrangianAdvectionEngine(
            wind_drift_factor=wind_drift_factor,
            wind_deflection_angle_deg=wind_deflection_angle_deg,
            horizontal_diffusion_coeff=diffusion_coefficient
        )

    def run_forecast(
        self,
        initial_polygon_geojson: Dict[str, Any],
        initial_time: datetime,
        currents_data: Dict[str, Any],
        wind_data: Dict[str, Any],
        stokes_data: Optional[Dict[str, Any]] = None,
        horizons_hours: List[int] = [6, 12, 24, 48],
        ensemble_size: int = 50
    ) -> Dict[str, Any]:
        """
        Executes Monte Carlo particle trajectory advection simulation.
        
        Returns dictionary containing:
        - "forecast_bands": List of bands per horizon and confidence level (50%, 80%, 95%)
        - "trajectory_track": List of mean centroids over time
        - "metocean_summary": Input forcing summary
        """
        poly_geom = shape(initial_polygon_geojson)
        centroid = poly_geom.centroid
        c_lon, c_lat = centroid.x, centroid.y

        # Initialize particles sampled uniformly across initial polygon boundary & interior
        n_particles = ensemble_size * 4
        # Generate initial cloud around centroid
        particle_lons = np.random.normal(c_lon, 0.005, size=n_particles)
        particle_lats = np.random.normal(c_lat, 0.005, size=n_particles)

        # Baseline metocean forcing
        u_curr_base = currents_data.get("u_mean", 0.15)
        v_curr_base = currents_data.get("v_mean", 0.10)
        u_wind_base = wind_data.get("u_wind_ms", 3.5)
        v_wind_base = wind_data.get("v_wind_ms", 2.5)
        u_stokes_base = stokes_data.get("u_stokes", 0.02) if stokes_data else 0.0
        v_stokes_base = stokes_data.get("v_stokes", 0.01) if stokes_data else 0.0

        all_bands = []
        trajectory_points = [{
            "horizon_hours": 0,
            "target_time": initial_time.isoformat(),
            "centroid_lon": round(c_lon, 6),
            "centroid_lat": round(c_lat, 6),
            "mean_speed_kmh": 0.0
        }]

        current_time = initial_time
        curr_lons = particle_lons.copy()
        curr_lats = particle_lats.copy()

        # Step through in 1-hour increments
        max_horizon = max(horizons_hours)
        for h in range(1, max_horizon + 1):
            current_time += timedelta(hours=1)

            # Perturb forcing fields for Monte Carlo uncertainty
            # Wind error growth ~ 10-15% per 12 hours
            wind_error_scale = 0.4 * (1.0 + (h / 24.0))
            curr_error_scale = 0.03 * (1.0 + (h / 24.0))

            u_wind_pert = u_wind_base + float(np.random.normal(0, wind_error_scale))
            v_wind_pert = v_wind_base + float(np.random.normal(0, wind_error_scale))
            u_curr_pert = u_curr_base + float(np.random.normal(0, curr_error_scale))
            v_curr_pert = v_curr_base + float(np.random.normal(0, curr_error_scale))

            curr_lons, curr_lats = self.advection_engine.step_particles(
                particle_lons=curr_lons,
                particle_lats=curr_lats,
                u_curr=u_curr_pert,
                v_curr=v_curr_pert,
                u_wind=u_wind_pert,
                v_wind=v_wind_pert,
                dt_seconds=3600.0,
                u_stokes=u_stokes_base,
                v_stokes=v_stokes_base
            )

            # If current hour is a target horizon, compute confidence bands
            if h in horizons_hours:
                mean_lon = float(np.mean(curr_lons))
                mean_lat = float(np.mean(curr_lats))
                dist_km = get_geodesic_distance_km(c_lon, c_lat, mean_lon, mean_lat)
                speed_kmh = round(dist_km / h, 2)

                trajectory_points.append({
                    "horizon_hours": h,
                    "target_time": current_time.isoformat(),
                    "centroid_lon": round(mean_lon, 6),
                    "centroid_lat": round(mean_lat, 6),
                    "mean_speed_kmh": speed_kmh
                })

                # Compute 50% (best guess), 80% (standard), 95% (conservative envelope) contours
                contours = compute_containment_contours_for_particles(
                    particle_lons=curr_lons,
                    particle_lats=curr_lats,
                    confidence_levels=[0.50, 0.80, 0.95]
                )

                for c in contours:
                    all_bands.append({
                        "horizon_hours": h,
                        "target_time": current_time,
                        "confidence_level": c["confidence_level"],
                        "geom_geojson": c["geom_geojson"],
                        "area_km2": c["area_km2"],
                        "centroid_lat": c["centroid_lat"],
                        "centroid_lon": c["centroid_lon"],
                        "mean_speed_kmh": speed_kmh
                    })

        return {
            "forecast_bands": all_bands,
            "trajectory_points": trajectory_points,
            "metocean_summary": {
                "u_curr": u_curr_base,
                "v_curr": v_curr_base,
                "u_wind": u_wind_base,
                "v_wind": v_wind_base,
                "ensemble_size": ensemble_size
            }
        }
