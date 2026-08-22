"""
Train SAR Oil Spill Segmentation Model (DeepLabV3+ or U-Net)

Usage:
  python scripts/train_segmentation.py --data-dir data/segmentation/krestenitis --model deeplabv3plus --epochs 10

Requires Krestenitis benchmark dataset in data/segmentation/krestenitis/ with:
  images/  — SAR tiles (PNG/TIFF)
  masks/   — 5-class segmentation masks
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from torch.utils.data import DataLoader, random_split

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ml.models.registry import create_segmentation_model, get_device
from backend.app.ml.training.dataset import SARDataset
from backend.app.ml.training.trainer import ModelTrainer


def collect_paths(data_dir: str):
    images_dir = os.path.join(data_dir, "images")
    masks_dir = os.path.join(data_dir, "masks")
    image_paths = sorted(glob.glob(os.path.join(images_dir, "*")))
    mask_paths = []
    for ip in image_paths:
        base = os.path.splitext(os.path.basename(ip))[0]
        candidates = [
            os.path.join(masks_dir, base + ext)
            for ext in (".png", ".tif", ".tiff", ".jpg")
        ]
        mask_paths.append(next((c for c in candidates if os.path.exists(c)), candidates[0]))
    return image_paths, mask_paths


def main():
    parser = argparse.ArgumentParser(description="Train SAR oil spill segmentation model")
    parser.add_argument("--data-dir", default="data/segmentation/krestenitis", help="Dataset root")
    parser.add_argument("--model", default="deeplabv3plus", choices=["deeplabv3plus", "unet"])
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--val-split", type=float, default=0.15)
    args = parser.parse_args()

    if not os.path.isdir(args.data_dir):
        logger.error(
            f"Dataset not found at {args.data_dir}. "
            "Download Krestenitis benchmark from Zenodo and place under data/segmentation/krestenitis/. "
            "See docs/DATASETS.md."
        )
        sys.exit(1)

    image_paths, mask_paths = collect_paths(args.data_dir)
    if not image_paths:
        logger.error(f"No images found in {args.data_dir}/images/")
        sys.exit(1)

    full_dataset = SARDataset(image_paths, mask_paths, is_train=True)
    val_size = max(1, int(len(full_dataset) * args.val_split))
    train_size = len(full_dataset) - val_size
    train_ds, val_ds = random_split(full_dataset, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = get_device(settings.DEVICE)
    model = create_segmentation_model(model_name=args.model, in_channels=1, num_classes=5, device=device)

    trainer = ModelTrainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        device=device,
        learning_rate=args.lr,
    )

    os.makedirs(settings.MODEL_CHECKPOINT_DIR, exist_ok=True)
    ckpt_path = os.path.join(settings.MODEL_CHECKPOINT_DIR, f"{args.model}_best.pt")

    best_metrics = trainer.run_training(num_epochs=args.epochs, checkpoint_path=ckpt_path)
    logger.info(f"Training complete. Best metrics: {best_metrics}")


if __name__ == "__main__":
    main()
