from __future__ import annotations

import argparse

from .config import MODEL_CONFIGS


def parse_csv_list(raw: str) -> list[str]:
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def parse_split_ratios(raw: str) -> list[float]:
    ratios = []
    for value in raw.split(","):
        stripped = value.strip()
        if not stripped:
            continue
        ratio = float(stripped)
        if ratio <= 0.0 or ratio >= 1.0:
            raise ValueError(f"Invalid split value: {ratio}. Use values between 0 and 1.")
        ratios.append(ratio)

    unique = sorted(set(ratios))
    if not unique:
        raise ValueError("At least one split ratio is required.")
    return unique


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "TensorFlow/Keras CIFAR-10 benchmark and submission generator "
            "(3 models, multiple train/test splits, metrics, ROC/AUC, Kaggle CSV prediction)."
        )
    )
    parser.add_argument("--data-root", type=str, default="data/cifar-10")
    parser.add_argument("--labels-file", type=str, default=None)
    parser.add_argument("--train-dir", type=str, default=None)
    parser.add_argument("--test-dir", type=str, default=None)
    parser.add_argument("--submission-template", type=str, default=None)
    parser.add_argument("--submission-file", type=str, default="submission_best.csv")
    parser.add_argument("--skip-submission", action="store_true")
    parser.add_argument("--max-test-images", type=int, default=None)
    parser.add_argument(
        "--models",
        type=str,
        default="mobilenetv2,efficientnetb0,resnet50",
        help=f"Comma-separated models: {', '.join(MODEL_CONFIGS.keys())}",
    )
    parser.add_argument(
        "--splits",
        type=str,
        default="0.7,0.8,0.85",
        help="Comma-separated train ratios for evaluation, e.g. 0.7,0.8,0.85.",
    )
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--image-size", type=int, default=160)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=2)
    parser.add_argument("--weights", type=str, choices=["imagenet", "none"], default="imagenet")
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--preview-samples", type=int, default=16)
    parser.add_argument("--output-dir", type=str, default="outputs")
    parser.add_argument("--save-models", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-level", type=str, default="INFO")
    return parser.parse_args()
