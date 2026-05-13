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


def parse_model_names(raw: str) -> list[str]:
    model_names = parse_csv_list(raw)
    if not model_names:
        raise ValueError("No models selected. Pass at least one value via --models.")

    invalid_models = [name for name in model_names if name not in MODEL_CONFIGS]
    if invalid_models:
        allowed = ", ".join(MODEL_CONFIGS.keys())
        raise ValueError(f"Unknown models: {invalid_models}. Allowed: {allowed}")

    return model_names


def validate_numeric_args(args: argparse.Namespace) -> None:
    if args.val_ratio <= 0.0 or args.val_ratio >= 0.5:
        raise ValueError("Validation ratio must be between 0 and 0.5.")
    if args.epochs <= 0:
        raise ValueError("--epochs must be > 0.")
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be > 0.")
    if args.image_size <= 0:
        raise ValueError("--image-size must be > 0.")
    if args.learning_rate <= 0.0:
        raise ValueError("--learning-rate must be > 0.")
    if args.patience < 0:
        raise ValueError("--patience must be >= 0.")
    if args.max_samples is not None and args.max_samples <= 0:
        raise ValueError("--max-samples must be > 0 when provided.")
    if args.max_test_images is not None and args.max_test_images <= 0:
        raise ValueError("--max-test-images must be > 0 when provided.")
    if args.preview_samples < 0:
        raise ValueError("--preview-samples must be >= 0.")
    if args.evaluate_split is not None and (args.evaluate_split <= 0.0 or args.evaluate_split >= 1.0):
        raise ValueError("--evaluate-split must be between 0 and 1 when provided.")
    if args.evaluate_model_name is not None and args.evaluate_model_name.lower() not in MODEL_CONFIGS:
        allowed = ", ".join(MODEL_CONFIGS.keys())
        raise ValueError(f"Unknown --evaluate-model-name: {args.evaluate_model_name}. Allowed: {allowed}")


def resolve_cli_choices(args: argparse.Namespace) -> tuple[list[str], list[float]]:
    model_names = parse_model_names(args.models)
    split_ratios = parse_split_ratios(args.splits)
    return model_names, split_ratios


def _add_data_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-root", type=str, default="data/cifar-10")
    parser.add_argument("--labels-file", type=str, default=None)
    parser.add_argument("--train-dir", type=str, default=None)
    parser.add_argument("--test-dir", type=str, default=None)


def _add_submission_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--submission-template", type=str, default=None)
    parser.add_argument("--submission-file", type=str, default="submission_best.csv")
    parser.add_argument("--skip-submission", action="store_true")
    parser.add_argument("--max-test-images", type=int, default=None)


def _add_experiment_args(parser: argparse.ArgumentParser) -> None:
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


def _add_training_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--image-size", type=int, default=160)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=2)
    parser.add_argument("--weights", type=str, choices=["imagenet", "none"], default="imagenet")
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--preview-samples", type=int, default=16)


def _add_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-dir", type=str, default="outputs")
    parser.add_argument("--save-models", action="store_true")
    parser.add_argument(
        "--evaluate-model-path",
        type=str,
        default=None,
        help="Validation-only mode: path to a trained model file (.weights.h5 or .keras).",
    )
    parser.add_argument(
        "--evaluate-model-name",
        type=str,
        default=None,
        help="Model name for --evaluate-model-path when loading weights (.weights.h5).",
    )
    parser.add_argument(
        "--evaluate-split",
        type=float,
        default=None,
        help="Original train split ratio (e.g. 0.9) for reconstructing the validation subset.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--log-level",
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "TensorFlow/Keras CIFAR-10 benchmark and submission generator "
            "(3 models, multiple train/test splits, metrics, ROC/AUC, Kaggle CSV prediction)."
        )
    )
    _add_data_args(parser)
    _add_submission_args(parser)
    _add_experiment_args(parser)
    _add_training_args(parser)
    _add_runtime_args(parser)
    return parser.parse_args()
