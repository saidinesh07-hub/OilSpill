"""
SAR Inference Engine
Performs end-to-end preprocessing, windowed neural inference, probability stitching, and confidence calibration.
"""
from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn.functional as F
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.constants import CLASS_ID_TO_NAME, CLASS_NAME_TO_ID
from backend.app.ml.models.registry import create_segmentation_model, get_device
from backend.app.ml.preprocessing.calibration import calibrate_sar_dn_to_sigma0
from backend.app.ml.preprocessing.normalization import normalize_sar_db
from backend.app.ml.preprocessing.speckle import lee_filter
from backend.app.ml.preprocessing.tiling import extract_tiles, stitch_probability_maps


class SARInferenceEngine:
    """
    Research-grade inference engine for Sentinel-1 SAR oil spill segmentation.
    """
    def __init__(
        self,
        model_name: str = "deeplabv3plus",
        checkpoint_path: Optional[str] = None,
        device: Optional[str] = None,
        tile_size: int = 256,
        tile_overlap: int = 32,
        batch_size: int = 8
    ):
        self.device = get_device(device)
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap
        self.batch_size = batch_size
        self.model_name = model_name
        
        self.model = create_segmentation_model(
            model_name=model_name,
            in_channels=1,
            num_classes=5,
            pretrained_weights_path=checkpoint_path,
            device=self.device
        )
        logger.info(f"Inference engine initialized with {model_name} on {self.device}")

    def preprocess_sar(self, raw_sar: np.ndarray, is_raw_dn: bool = False) -> np.ndarray:
        """
        Applies radiometric calibration (if raw DN), Lee speckle filtering, and dB normalization.
        """
        if is_raw_dn:
            sar_db = calibrate_sar_dn_to_sigma0(raw_sar)
        else:
            sar_db = raw_sar.astype(np.float32)

        # Despeckle with Lee filter
        despeckled = lee_filter(sar_db, window_size=5)
        # Normalize to [0, 1] range for neural net
        norm_img = normalize_sar_db(despeckled, min_db=-35.0, max_db=5.0)
        return norm_img

    def predict_full_scene(
        self,
        sar_image: np.ndarray,
        is_raw_dn: bool = False
    ) -> Dict[str, np.ndarray]:
        """
        Executes windowed inference across full SAR scene and stitches probability maps.
        
        Returns dictionary with:
        - "class_mask": 2D integer array [0..4]
        - "prob_maps": 3D float array [H, W, 5] (probabilities for all classes)
        - "oil_probability": 2D float array [0..1]
        - "lookalike_probability": 2D float array [0..1]
        - "confidence_map": 2D float array [0..1] (prediction confidence)
        """
        h, w = sar_image.shape[:2]
        norm_sar = self.preprocess_sar(sar_image, is_raw_dn=is_raw_dn)

        # Windowed Tiling
        tiles, boxes = extract_tiles(norm_sar, tile_size=self.tile_size, overlap=self.tile_overlap)
        
        tile_probabilities: List[np.ndarray] = []
        
        # Batch inference
        self.model.eval()
        with torch.no_grad():
            for i in range(0, len(tiles), self.batch_size):
                batch_tiles = tiles[i:i + self.batch_size]
                batch_tensors = torch.stack([
                    torch.from_numpy(t).unsqueeze(0).float() for t in batch_tiles
                ]).to(self.device)

                logits = self.model(batch_tensors)
                probs = F.softmax(logits, dim=1).cpu().numpy()  # [B, 5, H, W]

                for b in range(probs.shape[0]):
                    # Transpose to [H, W, 5]
                    tile_prob = np.transpose(probs[b], (1, 2, 0))
                    tile_probabilities.append(tile_prob)

        # Stitch full scene with Hann window blending
        stitched_probs = stitch_probability_maps(
            tile_probabilities=tile_probabilities,
            boxes=boxes,
            full_shape=(h, w, 5),
            tile_size=self.tile_size
        )

        class_mask = np.argmax(stitched_probs, axis=-1).astype(np.int32)
        confidence_map = np.max(stitched_probs, axis=-1).astype(np.float32)

        return {
            "class_mask": class_mask,
            "prob_maps": stitched_probs,
            "oil_probability": stitched_probs[:, :, 1],
            "lookalike_probability": stitched_probs[:, :, 2],
            "confidence_map": confidence_map
        }
