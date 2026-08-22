"""
Environmental MetOcean Data Interfaces
Defines abstract data providers for ocean currents, surface winds, and Stokes wave drift.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class MetOceanForcingProvider(ABC):
    """Abstract interface for environmental forcing providers."""

    @abstractmethod
    def get_surface_currents(
        self,
        bbox: List[float],  # [min_lon, min_lat, max_lon, max_lat]
        target_time: datetime
    ) -> Dict[str, Any]:
        """
        Retrieves surface ocean current field (u, v in m/s).
        Returns dict with: u_mean, v_mean, magnitude_mean, data_vintage, source, grid_vectors
        """
        pass

    @abstractmethod
    def get_surface_winds(
        self,
        bbox: List[float],
        target_time: datetime
    ) -> Dict[str, Any]:
        """
        Retrieves 10m surface wind field (u, v in m/s).
        Returns dict with: u_mean, v_mean, magnitude_mean, speed_knots, data_vintage, source
        """
        pass

    @abstractmethod
    def get_stokes_drift(
        self,
        bbox: List[float],
        target_time: datetime
    ) -> Dict[str, Any]:
        """
        Retrieves wave Stokes drift (u, v in m/s) and significant wave height (m).
        """
        pass
