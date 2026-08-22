"""
ML Model Registry and Factory
Manages architecture loading, device assignment, and checkpoint serialization.
"""
import os
from typing import Optional
import torch
import torch.nn as nn
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.unet import UNet
from backend.app.ml.models.deeplabv3plus import DeepLabV3Plus


def get_device(device_override: Optional[str] = None) -> torch.device:
    """Selects CUDA if requested and available, else CPU."""
    dev_str = device_override or settings.DEVICE
    if dev_str.lower() == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def create_segmentation_model(
    model_name: str = "deeplabv3plus",
    in_channels: int = 1,
    num_classes: int = 5,
    pretrained_weights_path: Optional[str] = None,
    device: Optional[torch.device] = None
) -> nn.Module:
    """
    Instantiates a 5-class segmentation model and loads weights if available.
    """
    dev = device or get_device()
    name = model_name.lower().strip()

    if name in ["deeplabv3plus", "deeplab", "deeplabv3+"]:
        model = DeepLabV3Plus(in_channels=in_channels, num_classes=num_classes)
    elif name in ["unet", "u_net"]:
        model = UNet(in_channels=in_channels, num_classes=num_classes)
    else:
        logger.warning(f"Unknown model name '{model_name}', falling back to DeepLabV3+.")
        model = DeepLabV3Plus(in_channels=in_channels, num_classes=num_classes)

    model = model.to(dev)

    if pretrained_weights_path and os.path.exists(pretrained_weights_path):
        try:
            logger.info(f"Loading checkpoint from: {pretrained_weights_path}")
            checkpoint = torch.load(pretrained_weights_path, map_location=dev)
            if "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"])
            else:
                model.load_state_dict(checkpoint)
            logger.info(f"Weights loaded successfully for {model_name}.")
        except Exception as e:
            logger.error(f"Failed to load weights from {pretrained_weights_path}: {e}")

    model.eval()
    return model


def save_checkpoint(
    model: nn.Module,
    optimizer: Optional[torch.optim.Optimizer],
    epoch: int,
    metrics: dict,
    save_path: str
):
    """Saves training checkpoint with epoch, model state, and evaluation metrics."""
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    payload = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict() if optimizer else None,
        "metrics": metrics
    }
    torch.save(payload, save_path)
    logger.info(f"Saved checkpoint to: {save_path}")
