"""
Lagrangian Particle Drift and MetOcean Advection Physics Engine
Implements hydrodynamic transport: Surface Current + 3% Wind Leeway (with Coriolis deflection) + Stokes Drift + Turbulent Diffusion.
"""
from typing import List, Tuple
import numpy as np
from backend.app.geospatial.geometry_ops import get_geodesic_forward_point


class LagrangianAdvectionEngine:
    """
    Simulates physical movement of oil particles over time interval dt.
    """
    def __init__(
        self,
        wind_drift_factor: float = 0.03,            # 3% wind leeway rule
        wind_deflection_angle_deg: float = 15.0,    # Coriolis deflection angle
        horizontal_diffusion_coeff: float = 2.0     # m2/s (turbulent oceanic eddy diffusion)
    ):
        self.wind_drift_factor = wind_drift_factor
        self.wind_deflection_angle_deg = wind_deflection_angle_deg
        self.horizontal_diffusion_coeff = horizontal_diffusion_coeff

    def compute_particle_velocity_vector(
        self,
        u_curr: float,
        v_curr: float,
        u_wind: float,
        v_wind: float,
        u_stokes: float = 0.0,
        v_stokes: float = 0.0
    ) -> Tuple[float, float]:
        """
        Calculates net transport velocity vector (u_net, v_net in m/s).
        Applies Coriolis rotation matrix to wind vector.
        """
        # Wind vector magnitude and angle
        theta_rad = np.radians(self.wind_deflection_angle_deg)
        cos_t = np.cos(theta_rad)
        sin_t = np.sin(theta_rad)

        # Deflected wind vector in m/s
        u_wind_deflected = self.wind_drift_factor * (u_wind * cos_t - v_wind * sin_t)
        v_wind_deflected = self.wind_drift_factor * (u_wind * sin_t + v_wind * cos_t)

        # Total advective velocity in m/s
        u_net = u_curr + u_wind_deflected + u_stokes
        v_net = v_curr + v_wind_deflected + v_stokes

        return u_net, v_net

    def step_particles(
        self,
        particle_lons: np.ndarray,
        particle_lats: np.ndarray,
        u_curr: float,
        v_curr: float,
        u_wind: float,
        v_wind: float,
        dt_seconds: float,
        u_stokes: float = 0.0,
        v_stokes: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Advances particle positions by dt_seconds using Eulerian-Lagrangian forward integration with diffusion.
        """
        u_net, v_net = self.compute_particle_velocity_vector(
            u_curr, v_curr, u_wind, v_wind, u_stokes, v_stokes
        )

        n_particles = len(particle_lons)

        # Turbulent diffusion displacement using Einstein random walk: std = sqrt(2 * D * dt)
        diff_std_m = np.sqrt(2.0 * self.horizontal_diffusion_coeff * dt_seconds)
        diff_x_m = np.random.normal(0.0, diff_std_m, size=n_particles)
        diff_y_m = np.random.normal(0.0, diff_std_m, size=n_particles)

        # Net displacements in meters
        dx_m = (u_net * dt_seconds) + diff_x_m
        dy_m = (v_net * dt_seconds) + diff_y_m

        # Convert meter displacements to geographic degrees (WGS84 approx: 1 deg lat ~ 111,320m)
        mean_lat = float(np.mean(particle_lats))
        m_per_deg_lat = 111320.0
        m_per_deg_lon = 111320.0 * np.cos(np.radians(mean_lat))
        m_per_deg_lon = max(m_per_deg_lon, 1000.0)

        new_lons = particle_lons + (dx_m / m_per_deg_lon)
        new_lats = particle_lats + (dy_m / m_per_deg_lat)

        return new_lons, new_lats
