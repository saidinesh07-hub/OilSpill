"""
Unit Tests for Machine Learning Models, Preprocessing, and Metrics
"""
import pytest
import numpy as np
import torch
from backend.app.ml.models.deeplabv3plus import DeepLabV3Plus
from backend.app.ml.models.unet import UNet
from backend.app.ml.evaluation.metrics import SegmentationEvaluator
from backend.app.ml.preprocessing.speckle import lee_filter
from backend.app.ml.preprocessing.normalization import normalize_sar_db


def test_deeplabv3plus_forward_shape():
    model = DeepLabV3Plus(in_channels=1, num_classes=5)
    dummy_input = torch.randn(2, 1, 256, 256)
    output = model(dummy_input)
    assert output.shape == (2, 5, 256, 256)


def test_unet_forward_shape():
    model = UNet(in_channels=1, num_classes=5, base_features=16)
    dummy_input = torch.randn(2, 1, 256, 256)
    output = model(dummy_input)
    assert output.shape == (2, 5, 256, 256)


def test_segmentation_evaluator_metrics():
    evaluator = SegmentationEvaluator(num_classes=5)
    # Perfect match test
    target = np.array([[0, 1], [2, 3]])
    pred = np.array([[0, 1], [2, 3]])
    evaluator.update(pred, target)
    metrics = evaluator.compute_metrics()

    assert metrics["mean_iou"] == 1.0
    assert metrics["overall_pixel_accuracy"] == 1.0
    assert metrics["lookalike_false_positive_rate"] == 0.0


def test_lookalike_false_positive_metric():
    evaluator = SegmentationEvaluator(num_classes=5)
    # Target has lookalike (class 2), predicted as oil (class 1)
    target = np.array([[2, 2], [0, 0]])
    pred = np.array([[1, 1], [0, 0]])
    evaluator.update(pred, target)
    metrics = evaluator.compute_metrics()

    assert metrics["lookalike_false_positive_rate"] == 1.0
    assert metrics["per_class"]["oil_spill"]["precision"] == 0.0


def test_lee_filter_despeckling():
    # Constant sea + heavy speckle noise
    clean_val = -20.0
    noisy = clean_val + np.random.normal(0, 4.0, size=(100, 100)).astype(np.float32)
    filtered = lee_filter(noisy, window_size=5)

    # Variance should be reduced after despeckling
    assert np.var(filtered) < np.var(noisy)
    # Mean backscatter should be preserved
    assert abs(np.mean(filtered) - clean_val) < 1.0
