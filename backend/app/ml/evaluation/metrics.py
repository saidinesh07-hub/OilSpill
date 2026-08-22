"""
Evaluation Metrics for SAR Oil Spill & Look-Alike Segmentation
Computes IoU, Dice/F1, Precision, Recall, Confusion Matrix, and Look-alike False Positive Rate.
"""
from typing import Dict, List, Optional
import numpy as np
from backend.app.ml.constants import CLASS_NAMES, CLASS_ID_TO_NAME


class SegmentationEvaluator:
    """
    Accumulates confusion matrix across evaluation batches and calculates per-class metrics.
    """
    def __init__(self, num_classes: int = 5, class_names: Optional[List[str]] = None):
        self.num_classes = num_classes
        self.class_names = class_names or CLASS_NAMES
        self.confusion_matrix = np.zeros((num_classes, num_classes), dtype=np.int64)

    def reset(self):
        self.confusion_matrix.fill(0)

    def update(self, pred_mask: np.ndarray, target_mask: np.ndarray):
        """
        Updates confusion matrix with predicted and ground-truth integer label masks.
        pred_mask, target_mask: 2D or flattened arrays with values in [0, num_classes - 1]
        """
        pred_flat = pred_mask.flatten().astype(np.int64)
        target_flat = target_mask.flatten().astype(np.int64)

        # Filter valid class range
        valid_idx = (target_flat >= 0) & (target_flat < self.num_classes) & \
                    (pred_flat >= 0) & (pred_flat < self.num_classes)

        p = pred_flat[valid_idx]
        t = target_flat[valid_idx]

        # 2D histogram
        hist = np.bincount(
            self.num_classes * t + p,
            minlength=self.num_classes ** 2
        ).reshape(self.num_classes, self.num_classes)

        self.confusion_matrix += hist

    def compute_metrics(self) -> Dict[str, any]:
        """
        Calculates per-class and macro-averaged metrics from accumulated confusion matrix.
        """
        cm = self.confusion_matrix
        tp = np.diag(cm).astype(np.float64)
        fp = (np.sum(cm, axis=0) - tp).astype(np.float64)  # sum along columns = total predicted
        fn = (np.sum(cm, axis=1) - tp).astype(np.float64)  # sum along rows = total ground truth
        total = np.sum(cm)

        # Intersection over Union (IoU) = TP / (TP + FP + FN)
        denominator_iou = tp + fp + fn
        per_class_iou = np.zeros(self.num_classes, dtype=np.float64)
        with np.errstate(divide='ignore', invalid='ignore'):
            valid_mask = denominator_iou > 0
            per_class_iou[valid_mask] = tp[valid_mask] / denominator_iou[valid_mask]

        # Dice / F1 = 2*TP / (2*TP + FP + FN)
        denominator_dice = 2 * tp + fp + fn
        per_class_dice = np.zeros(self.num_classes, dtype=np.float64)
        with np.errstate(divide='ignore', invalid='ignore'):
            valid_mask = denominator_dice > 0
            per_class_dice[valid_mask] = (2 * tp[valid_mask]) / denominator_dice[valid_mask]

        # Precision = TP / (TP + FP)
        denominator_prec = tp + fp
        per_class_precision = np.zeros(self.num_classes, dtype=np.float64)
        with np.errstate(divide='ignore', invalid='ignore'):
            valid_mask = denominator_prec > 0
            per_class_precision[valid_mask] = tp[valid_mask] / denominator_prec[valid_mask]

        # Recall = TP / (TP + FN)
        denominator_rec = tp + fn
        per_class_recall = np.zeros(self.num_classes, dtype=np.float64)
        with np.errstate(divide='ignore', invalid='ignore'):
            valid_mask = denominator_rec > 0
            per_class_recall[valid_mask] = tp[valid_mask] / denominator_rec[valid_mask]

        # Pixel Accuracy = sum(TP) / total
        overall_pixel_acc = float(np.sum(tp) / max(total, 1))

        # Look-alike False Positive Rate (look-alikes falsely flagged as oil spill)
        oil_idx = 1
        lookalike_idx = 2
        lookalikes_as_oil = int(cm[lookalike_idx, oil_idx])  # true is lookalike, pred is oil
        total_true_lookalikes = int(np.sum(cm[lookalike_idx, :]))
        lookalike_fp_rate = float(lookalikes_as_oil / max(total_true_lookalikes, 1))

        per_class_results = {}
        present_classes_iou = []
        for i, name in enumerate(self.class_names):
            has_presence = denominator_iou[i] > 0
            if has_presence:
                present_classes_iou.append(per_class_iou[i])
            per_class_results[name] = {
                "class_id": i,
                "iou": float(per_class_iou[i]),
                "dice": float(per_class_dice[i]),
                "precision": float(per_class_precision[i]),
                "recall": float(per_class_recall[i]),
                "true_pixel_count": int(np.sum(cm[i, :])),
                "pred_pixel_count": int(np.sum(cm[:, i]))
            }

        # Mean IoU over present classes
        mean_iou = float(np.mean(present_classes_iou)) if present_classes_iou else 0.0
        oil_spill_iou = float(per_class_iou[oil_idx]) if len(per_class_iou) > oil_idx else 0.0
        look_alike_iou = float(per_class_iou[lookalike_idx]) if len(per_class_iou) > lookalike_idx else 0.0

        return {
            "mean_iou": round(mean_iou, 4),
            "oil_spill_iou": round(oil_spill_iou, 4),
            "look_alike_iou": round(look_alike_iou, 4),
            "overall_pixel_accuracy": round(overall_pixel_acc, 4),
            "lookalike_false_positive_rate": round(lookalike_fp_rate, 4),
            "per_class": per_class_results,
            "confusion_matrix": cm.tolist()
        }
