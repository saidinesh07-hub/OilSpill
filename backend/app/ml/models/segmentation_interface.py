"""
Modular Oil Spill Segmentation Model Interface
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np
import torch
import torch.nn as nn
from backend.app.ml.inference.engine import SARInferenceEngine
from backend.app.ml.models.registry import create_segmentation_model, get_device, save_checkpoint


class OilSpillSegmentationModel(ABC):
    @abstractmethod
    def predict(self, sar_image: np.ndarray, is_raw_dn: bool = False) -> Dict[str, np.ndarray]:
        ...

    @abstractmethod
    def predict_batch(self, tiles: List[np.ndarray], is_raw_dn: bool = False) -> List[Dict[str, np.ndarray]]:
        ...

    @abstractmethod
    def load_checkpoint(self, path: str) -> None:
        ...


class DeepLabSegmentationModel(OilSpillSegmentationModel):
    """Production inference wrapper around SARInferenceEngine."""

    def __init__(
        self,
        model_name: str = "deeplabv3plus",
        checkpoint_path: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.engine = SARInferenceEngine(
            model_name=model_name,
            checkpoint_path=checkpoint_path,
            device=device,
        )
        self.model_name = model_name
        self.checkpoint_path = checkpoint_path
        self._evaluated = checkpoint_path is not None

    def predict(self, sar_image: np.ndarray, is_raw_dn: bool = False) -> Dict[str, np.ndarray]:
        result = self.engine.predict_full_scene(sar_image, is_raw_dn=is_raw_dn)
        result["model_evaluated"] = self._evaluated
        result["model_version"] = f"{self.model_name}{'-trained' if self._evaluated else '-untrained'}"
        return result

    def predict_batch(self, tiles: List[np.ndarray], is_raw_dn: bool = False) -> List[Dict[str, np.ndarray]]:
        return [self.predict(tile, is_raw_dn=is_raw_dn) for tile in tiles]

    def load_checkpoint(self, path: str) -> None:
        self.engine.model = create_segmentation_model(
            model_name=self.model_name,
            pretrained_weights_path=path,
            device=self.engine.device,
        )
        self.checkpoint_path = path
        self._evaluated = True


def get_classification_label(predicted_class: str, confidence: float, lookalike_risk: float) -> str:
    """Human-readable classification without overclaiming certainty."""
    if predicted_class == "oil_spill":
        if confidence >= 0.85 and lookalike_risk < 0.25:
            return "Potential Oil Slick — High Confidence"
        if confidence >= 0.60:
            return "Potential Oil Slick — Moderate Confidence"
        return "Potential Oil Slick — Low Confidence"
    if predicted_class == "look_alike":
        return "Look-Alike Candidate"
    return predicted_class.replace("_", " ").title()
