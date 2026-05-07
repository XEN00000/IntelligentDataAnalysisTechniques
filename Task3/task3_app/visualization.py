from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import auc, roc_curve


def save_confusion_matrix_plot(
    cm: np.ndarray,
    labels: list[str],
    title: str,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))
    heatmap = ax.imshow(cm, cmap="Blues")
    fig.colorbar(heatmap, ax=ax)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_title(title)

    for row in range(cm.shape[0]):
        for col in range(cm.shape[1]):
            value = cm[row, col]
            ax.text(col, row, str(value), ha="center", va="center", color="black", fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def save_roc_plot(y_true_bin: np.ndarray, y_prob: np.ndarray, title: str, output_path: Path) -> float:
    fpr, tpr, _ = roc_curve(y_true_bin.ravel(), y_prob.ravel())
    roc_micro_auc = auc(fpr, tpr)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fpr, tpr, color="darkorange", lw=2, label=f"Micro-average ROC (AUC={roc_micro_auc:.4f})")
    ax.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(title)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return float(roc_micro_auc)


def save_prediction_preview(
    images: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: list[str],
    output_path: Path,
    sample_count: int,
    seed: int,
) -> None:
    count = min(sample_count, len(images))
    if count == 0:
        return

    rng = np.random.default_rng(seed)
    selected = rng.choice(len(images), size=count, replace=False)
    cols = 4
    rows = int(np.ceil(count / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(14, 3.5 * rows))
    axes = np.atleast_1d(axes).ravel()

    for index, axis in enumerate(axes):
        if index >= count:
            axis.axis("off")
            continue

        sample_idx = selected[index]
        axis.imshow(images[sample_idx].astype(np.uint8))
        true_label = labels[int(y_true[sample_idx])]
        pred_label = labels[int(y_pred[sample_idx])]
        color = "green" if y_true[sample_idx] == y_pred[sample_idx] else "red"
        axis.set_title(f"T: {true_label}\nP: {pred_label}", color=color, fontsize=9)
        axis.axis("off")

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
