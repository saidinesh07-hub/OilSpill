"""
Satellite Data Provider Interface
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np
from backend.app.schemas.data_contract import DataStatus, SceneMetadata


class SatelliteDataProvider(ABC):
    """Abstract provider for satellite SAR scene access."""

    @abstractmethod
    def search_scenes(
        self,
        bbox: List[float],
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    def load_scene_raster(
        self,
        scene_ref: str,
        band_index: int = 1,
    ) -> tuple[np.ndarray, SceneMetadata]:
        ...

    @abstractmethod
    def get_data_status(self) -> DataStatus:
        ...
