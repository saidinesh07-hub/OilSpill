"""
SAR Windowed Tiling and Stitching Module
Extracts overlapping 256x256 tiles and stitches probability fields with smooth blending.
"""
from typing import List, Tuple
import numpy as np


def generate_tile_grid(
    height: int,
    width: int,
    tile_size: int = 256,
    overlap: int = 32
) -> List[Tuple[int, int, int, int]]:
    """
    Generates (y_min, y_max, x_min, x_max) bounding boxes for tiling an image.
    Ensures complete coverage of boundaries.
    """
    stride = tile_size - overlap
    boxes = []

    y_starts = list(range(0, height - tile_size + 1, stride))
    if not y_starts or y_starts[-1] + tile_size < height:
        y_starts.append(max(0, height - tile_size))

    x_starts = list(range(0, width - tile_size + 1, stride))
    if not x_starts or x_starts[-1] + tile_size < width:
        x_starts.append(max(0, width - tile_size))

    for y in y_starts:
        for x in x_starts:
            boxes.append((y, min(y + tile_size, height), x, min(x + tile_size, width)))

    return boxes


def extract_tiles(
    image: np.ndarray,
    tile_size: int = 256,
    overlap: int = 32
) -> Tuple[List[np.ndarray], List[Tuple[int, int, int, int]]]:
    """
    Extracts tiles from 2D or 3D numpy array.
    """
    h, w = image.shape[:2]
    boxes = generate_tile_grid(h, w, tile_size=tile_size, overlap=overlap)
    tiles = []

    for y0, y1, x0, x1 in boxes:
        tile = image[y0:y1, x0:x1]
        # Pad if smaller than tile_size (at extreme boundaries)
        if tile.shape[0] < tile_size or tile.shape[1] < tile_size:
            pad_y = tile_size - tile.shape[0]
            pad_x = tile_size - tile.shape[1]
            if tile.ndim == 3:
                tile = np.pad(tile, ((0, pad_y), (0, pad_x), (0, 0)), mode="reflect")
            else:
                tile = np.pad(tile, ((0, pad_y), (0, pad_x)), mode="reflect")
        tiles.append(tile)

    return tiles, boxes


def create_2d_window(tile_size: int = 256) -> np.ndarray:
    """Creates a 2D Hann window for smooth tile blending."""
    w1 = np.hanning(tile_size)
    w2d = np.outer(w1, w1)
    return np.maximum(w2d, 1e-4)


def stitch_probability_maps(
    tile_probabilities: List[np.ndarray],
    boxes: List[Tuple[int, int, int, int]],
    full_shape: Tuple[int, int, int],  # (H, W, NumClasses)
    tile_size: int = 256
) -> np.ndarray:
    """
    Reconstructs full-scene probability map from tile predictions using Hann window weighting.
    """
    h, w, num_classes = full_shape
    accum_probs = np.zeros((h, w, num_classes), dtype=np.float32)
    accum_weights = np.zeros((h, w, 1), dtype=np.float32)
    
    window = create_2d_window(tile_size)[:, :, np.newaxis]

    for prob_tile, (y0, y1, x0, x1) in zip(tile_probabilities, boxes):
        actual_h = y1 - y0
        actual_w = x1 - x0
        
        valid_prob = prob_tile[:actual_h, :actual_w, :]
        valid_win = window[:actual_h, :actual_w, :]

        accum_probs[y0:y1, x0:x1, :] += valid_prob * valid_win
        accum_weights[y0:y1, x0:x1, :] += valid_win

    # Normalize by accumulated weights
    blended = accum_probs / np.maximum(accum_weights, 1e-7)
    return blended
