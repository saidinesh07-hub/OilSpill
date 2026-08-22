"""
PyTorch Dataset and Augmentations for SAR Oil Spill Segmentation
Handles 5-class Krestenitis dataset format and synthetic SAR benchmarks.
"""
import os
import random
from typing import List, Optional, Tuple
import numpy as np
import torch
from torch.utils.data import Dataset
from PIL import Image


class SARDataset(Dataset):
    """
    PyTorch Dataset for Sentinel-1 SAR tiles and 5-class segmentation masks.
    """
    def __init__(
        self,
        image_paths: List[str],
        mask_paths: List[str],
        is_train: bool = True,
        tile_size: int = 256
    ):
        assert len(image_paths) == len(mask_paths), "Images and masks count mismatch"
        self.image_paths = image_paths
        self.mask_paths = mask_paths
        self.is_train = is_train
        self.tile_size = tile_size

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        img_path = self.image_paths[idx]
        mask_path = self.mask_paths[idx]

        # Load image as grayscale float in [0, 1]
        if os.path.exists(img_path):
            img = Image.open(img_path).convert("L")
            img_arr = np.array(img, dtype=np.float32) / 255.0
        else:
            # Fallback zero array if test mock
            img_arr = np.zeros((self.tile_size, self.tile_size), dtype=np.float32)

        # Load mask as integer class IDs [0..4]
        if os.path.exists(mask_path):
            mask = Image.open(mask_path)
            mask_arr = np.array(mask, dtype=np.int64)
            # Map values if masks are saved as RGB or specific color codes
            if mask_arr.ndim == 3:
                mask_arr = self._rgb_to_class_id(mask_arr)
            # Clip to valid range [0, 4]
            mask_arr = np.clip(mask_arr, 0, 4)
        else:
            mask_arr = np.zeros((self.tile_size, self.tile_size), dtype=np.int64)

        # Augmentations for training
        if self.is_train:
            img_arr, mask_arr = self._augment(img_arr, mask_arr)

        # To PyTorch tensors: Image [1, H, W], Mask [H, W]
        img_tensor = torch.from_numpy(img_arr).unsqueeze(0).float()
        mask_tensor = torch.from_numpy(mask_arr).long()

        return img_tensor, mask_tensor

    def _augment(self, img: np.ndarray, mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        # Random Horizontal Flip
        if random.random() > 0.5:
            img = np.fliplr(img).copy()
            mask = np.fliplr(mask).copy()

        # Random Vertical Flip
        if random.random() > 0.5:
            img = np.flipud(img).copy()
            mask = np.flipud(mask).copy()

        # Random 90-degree Rotation
        k = random.randint(0, 3)
        if k > 0:
            img = np.rot90(img, k).copy()
            mask = np.rot90(mask, k).copy()

        # Add subtle multiplicative speckle noise simulation to SAR intensity
        if random.random() > 0.6:
            noise = np.random.gamma(shape=4.0, scale=0.25, size=img.shape).astype(np.float32)
            img = np.clip(img * noise, 0.0, 1.0)

        return img, mask

    @staticmethod
    def _rgb_to_class_id(rgb_mask: np.ndarray) -> np.ndarray:
        """Helper to convert standard Krestenitis RGB colored masks to class IDs."""
        # 0: Sea (Dark/Navy/Black), 1: Oil (Cyan/Red), 2: Lookalike (Brown/Yellow), 3: Ship (White/Purple), 4: Land (Green/Red)
        h, w = rgb_mask.shape[:2]
        class_mask = np.zeros((h, w), dtype=np.int64)
        r, g, b = rgb_mask[:, :, 0], rgb_mask[:, :, 1], rgb_mask[:, :, 2]
        
        # Heuristic RGB mapping if dataset uses colored masks
        oil_pixels = (r > 150) & (g < 100) & (b < 100)  # Reddish
        lookalike_pixels = (r > 150) & (g > 100) & (b < 80)  # Yellow/Orange
        ship_pixels = (r < 50) & (g > 150) & (b > 150)  # Cyan
        land_pixels = (r < 100) & (g > 150) & (b < 100)  # Green

        class_mask[oil_pixels] = 1
        class_mask[lookalike_pixels] = 2
        class_mask[ship_pixels] = 3
        class_mask[land_pixels] = 4
        return class_mask
