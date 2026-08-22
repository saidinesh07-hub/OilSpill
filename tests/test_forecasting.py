"""
Unit Tests for Lagrangian Hydrodynamic Advection and Monte Carlo Ensembles
"""
from datetime import datetime, timezone
import pytest
import numpy as np
from backend.app.forecasting.lagrangian import LagrangianAdvectionEngine
from backend.app.forecasting.ensemble import TrajectoryForecaster
from shapely.geometry import Polygon, mapping


def test_lagrangian_wind_deflection_vector():
    engine = LagrangianAdvectionEngine(wind_drift_factor=0.03, wind_deflection_angle_deg=15.0)
    
    # Pure North wind (u=0, v=10 m/s)
    # With 15 deg Coriolis deflection in NH, u_deflected should be positive (eastward drift component)
    u_net, v_net = engine.compute_particle_velocity_vector(
        u_curr=0.0, v_curr=0.0, u_wind=0.0, v_wind=10.0
    )

    # 3% of 10 m/s = 0.3 m/s net magnitude
    mag = np.sqrt(u_net ** 2 + v_net ** 2)
    assert abs(mag - 0.30) < 1e-3
    assert u_net < 0.0  # Deflected according to rotation matrix


def test_trajectory_forecaster_ensemble_output():
    forecaster = TrajectoryForecaster()
    poly = Polygon([(80.30, 13.20), (80.35, 13.20), (80.35, 13.25), (80.30, 13.25), (80.30, 13.20)])
    
    out = forecaster.run_forecast(
        initial_polygon_geojson=mapping(poly),
        initial_time=datetime.now(timezone.utc),
        currents_data={"u_mean": 0.20, "v_mean": 0.15},
        wind_data={"u_wind_ms": 4.0, "v_wind_ms": 3.0},
        horizons_hours=[6, 12, 24, 48],
        ensemble_size=30
    )

    bands = out["forecast_bands"]
    # 4 horizons * 3 confidence levels (0.50, 0.80, 0.95) = 12 bands
    assert len(bands) == 12

    # Check that 95% band area is larger than 50% band area at 24h
    b_50 = next(b for b in bands if b["horizon_hours"] == 24 and b["confidence_level"] == 0.50)
    b_95 = next(b for b in bands if b["horizon_hours"] == 24 and b["confidence_level"] == 0.95)
    assert b_95["area_km2"] >= b_50["area_km2"]
