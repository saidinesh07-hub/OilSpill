"""
ML Training Pipeline for SAR Oil Spill Segmentation
Implements Combined Weighted Cross-Entropy + Multiclass Soft Dice Loss.
"""
from typing import Dict, List, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from backend.app.core.logging import logger
from backend.app.ml.constants import DEFAULT_CLASS_WEIGHTS
from backend.app.ml.evaluation.metrics import SegmentationEvaluator
from backend.app.ml.models.registry import save_checkpoint


class MulticlassDiceLoss(nn.Module):
    """
    Multiclass Soft Dice Loss to counteract extreme foreground/background class imbalance.
    """
    def __init__(self, num_classes: int = 5, smooth: float = 1.0, ignore_index: Optional[int] = None):
        super().__init__()
        self.num_classes = num_classes
        self.smooth = smooth
        self.ignore_index = ignore_index

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        probs = F.softmax(logits, dim=1)
        targets_one_hot = F.one_hot(targets, num_classes=self.num_classes).permute(0, 3, 1, 2).float()

        dice_losses = []
        for c in range(self.num_classes):
            if self.ignore_index is not None and c == self.ignore_index:
                continue
            pred_c = probs[:, c, :, :]
            target_c = targets_one_hot[:, c, :, :]

            intersection = torch.sum(pred_c * target_c)
            cardinality = torch.sum(pred_c + target_c)

            dice = (2.0 * intersection + self.smooth) / (cardinality + self.smooth)
            dice_losses.append(1.0 - dice)

        return torch.mean(torch.stack(dice_losses))


class CombinedSegmentationLoss(nn.Module):
    """Combines Class-Weighted Cross Entropy and Soft Dice Loss."""
    def __init__(self, num_classes: int = 5, class_weights: Optional[List[float]] = None):
        super().__init__()
        weights = torch.tensor(class_weights or DEFAULT_CLASS_WEIGHTS, dtype=torch.float32)
        self.ce = nn.CrossEntropyLoss(weight=weights)
        self.dice = MulticlassDiceLoss(num_classes=num_classes)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_loss = self.ce(logits, targets)
        dice_loss = self.dice(logits, targets)
        return ce_loss + dice_loss


class ModelTrainer:
    """
    Orchestrates training, validation, evaluation, and checkpointing.
    """
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        device: torch.device,
        learning_rate: float = 1e-4,
        class_weights: Optional[List[float]] = None
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=1e-4)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode='max', factor=0.5, patience=3)
        self.criterion = CombinedSegmentationLoss(class_weights=class_weights).to(device)
        self.evaluator = SegmentationEvaluator(num_classes=5)

    def train_epoch(self) -> float:
        self.model.train()
        total_loss = 0.0

        for images, masks in self.train_loader:
            images = images.to(self.device)
            masks = masks.to(self.device)

            self.optimizer.zero_grad()
            logits = self.model(images)
            loss = self.criterion(logits, masks)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        return total_loss / max(len(self.train_loader), 1)

    def validate(self) -> Dict[str, any]:
        self.model.eval()
        self.evaluator.reset()
        val_loss = 0.0

        with torch.no_grad():
            for images, masks in self.val_loader:
                images = images.to(self.device)
                masks = masks.to(self.device)

                logits = self.model(images)
                loss = self.criterion(logits, masks)
                val_loss += loss.item()

                preds = torch.argmax(logits, dim=1).cpu().numpy()
                targets = masks.cpu().numpy()
                self.evaluator.update(preds, targets)

        metrics = self.evaluator.compute_metrics()
        metrics["val_loss"] = round(val_loss / max(len(self.val_loader), 1), 4)
        return metrics

    def run_training(self, num_epochs: int = 10, checkpoint_path: str = "./ml/experiments/checkpoints/best_model.pt") -> Dict[str, any]:
        logger.info(f"Starting training for {num_epochs} epochs on device: {self.device}")
        best_oil_iou = 0.0
        best_metrics = {}

        for epoch in range(1, num_epochs + 1):
            train_loss = self.train_epoch()
            val_metrics = self.validate()
            self.scheduler.step(val_metrics["oil_spill_iou"])

            logger.info(
                f"Epoch [{epoch}/{num_epochs}] Train Loss: {train_loss:.4f} | "
                f"Val Loss: {val_metrics['val_loss']:.4f} | "
                f"mIoU: {val_metrics['mean_iou']:.4f} | "
                f"Oil IoU: {val_metrics['oil_spill_iou']:.4f} | "
                f"Look-alike FP Rate: {val_metrics['lookalike_false_positive_rate']:.4f}"
            )

            if val_metrics["oil_spill_iou"] >= best_oil_iou:
                best_oil_iou = val_metrics["oil_spill_iou"]
                best_metrics = val_metrics
                save_checkpoint(self.model, self.optimizer, epoch, val_metrics, checkpoint_path)

        return best_metrics
