from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .cli import parse_args, resolve_cli_choices, validate_numeric_args
from .config import CIFAR10_LABELS, MODEL_CONFIGS
from .data import (
    collect_test_paths,
    load_train_arrays,
    load_training_frame,
    resolve_dataset_paths,
    setup_seed,
)
from .experiment import (
    evaluate_trained_model_on_validation,
    experiment_tag,
    run_experiment,
    train_best_model_on_full_train,
)
from .logging_utils import LOGGER, configure_logging
from .submission import build_submission_csv


def _infer_evaluation_target_from_filename(model_path: Path) -> tuple[str, float] | None:
    match = re.match(
        r"^(?P<model>[a-z0-9]+)_train(?P<train>\d+)_test(?P<test>\d+)(?:\.weights\.h5|\.keras)$",
        model_path.name.lower(),
    )
    if not match:
        return None

    train_pct = int(match.group("train"))
    test_pct = int(match.group("test"))
    if train_pct + test_pct != 100:
        raise ValueError(
            f"Cannot infer split ratio from {model_path.name}: train% + test% must equal 100."
        )
    return match.group("model"), train_pct / 100.0


def _resolve_validation_check_target(args: argparse.Namespace) -> tuple[Path, str, float]:
    model_path = Path(args.evaluate_model_path).expanduser()
    if not model_path.exists():
        raise FileNotFoundError(f"--evaluate-model-path file not found: {model_path}")

    inferred = _infer_evaluation_target_from_filename(model_path)
    model_name = args.evaluate_model_name
    split_ratio = args.evaluate_split

    if model_name is None and inferred is not None:
        model_name = inferred[0]
    if split_ratio is None and inferred is not None:
        split_ratio = inferred[1]

    if model_name is None:
        raise ValueError(
            "Could not determine model name. Pass --evaluate-model-name or use a file name like "
            "'resnet50_train90_test10.weights.h5'."
        )
    model_name = str(model_name).strip().lower()
    if model_name not in MODEL_CONFIGS:
        allowed = ", ".join(MODEL_CONFIGS.keys())
        raise ValueError(f"Unknown evaluation model: {model_name}. Allowed: {allowed}")

    if split_ratio is None:
        raise ValueError(
            "Could not determine split ratio. Pass --evaluate-split or use a file name like "
            "'resnet50_train90_test10.weights.h5'."
        )
    split_ratio = float(split_ratio)
    if split_ratio <= 0.0 or split_ratio >= 1.0:
        raise ValueError("--evaluate-split must be between 0 and 1.")

    return model_path, model_name, split_ratio


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    setup_seed(args.seed)
    validate_numeric_args(args)

    train_dir, test_dir, labels_csv, sample_submission = resolve_dataset_paths(args)
    LOGGER.info("Dataset resolved: train_dir=%s test_dir=%s labels=%s", train_dir, test_dir, labels_csv)

    output_dir = Path(args.output_dir)
    plots_dir = output_dir / "plots"
    models_dir = output_dir / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Loading training labels from: %s", labels_csv)
    LOGGER.info("Loading training images from: %s", train_dir)
    training_frame = load_training_frame(
        labels_csv=labels_csv,
        train_dir=train_dir,
        max_samples=args.max_samples,
        seed=args.seed,
    )
    images, labels = load_train_arrays(training_frame)
    LOGGER.info("Prepared training arrays: images=%s labels=%s", images.shape, labels.shape)

    if args.evaluate_model_path:
        model_path, model_name, split_ratio = _resolve_validation_check_target(args)
        validation_result = evaluate_trained_model_on_validation(
            model_name=model_name,
            config=MODEL_CONFIGS[model_name],
            split_ratio=split_ratio,
            model_path=model_path,
            images=images,
            labels=labels,
            class_labels=CIFAR10_LABELS,
            args=args,
            plots_dir=plots_dir,
        )
        validation_json = output_dir / f"validation_check_{model_name}_{experiment_tag(split_ratio)}.json"
        validation_json.write_text(
            json.dumps(validation_result, indent=2),
            encoding="utf-8",
        )
        LOGGER.info("Validation check result written to: %s", validation_json.resolve())
        LOGGER.info("Artifacts written to: %s", output_dir.resolve())
        return

    model_names, split_ratios = resolve_cli_choices(args)

    all_results: list[dict[str, float | str | int]] = []
    for split_ratio in split_ratios:
        x_train, x_test, y_train, y_test = train_test_split(
            images,
            labels,
            train_size=split_ratio,
            stratify=labels,
            random_state=args.seed,
        )
        LOGGER.info(
            "Created split train=%.2f test=%.2f (train_samples=%d, test_samples=%d)",
            split_ratio,
            1.0 - split_ratio,
            len(x_train),
            len(x_test),
        )

        for model_name in model_names:
            result = run_experiment(
                model_name=model_name,
                config=MODEL_CONFIGS[model_name],
                split_ratio=split_ratio,
                x_train=x_train,
                x_test=x_test,
                y_train=y_train,
                y_test=y_test,
                labels=CIFAR10_LABELS,
                args=args,
                plots_dir=plots_dir,
                models_dir=models_dir,
            )
            all_results.append(result)

    results_df = pd.DataFrame(all_results).sort_values(
        by=["split_train_ratio", "macro_f1", "accuracy"],
        ascending=[True, False, False],
    )
    summary_csv = output_dir / "summary.csv"
    summary_json = output_dir / "summary.json"
    results_df.to_csv(summary_csv, index=False)
    summary_json.write_text(results_df.to_json(orient="records", indent=2), encoding="utf-8")

    best_by_split = (
        results_df.sort_values(by=["split_train_ratio", "macro_f1"], ascending=[True, False])
        .groupby("split_train_ratio", as_index=False)
        .first()
    )
    best_by_split.to_csv(output_dir / "best_models_by_split.csv", index=False)

    best_overall = results_df.sort_values(by=["macro_f1", "accuracy"], ascending=[False, False]).iloc[0]
    best_overall_path = output_dir / "best_overall.json"
    best_overall_path.write_text(
        json.dumps(
            best_overall.to_dict(),
            indent=2,
            default=lambda value: float(value)
            if isinstance(value, (np.floating, np.integer))
            else str(value),
        ),
        encoding="utf-8",
    )

    LOGGER.info("Best model per split (macro F1):")
    for _, row in best_by_split.iterrows():
        LOGGER.info(
            "split=%.2f/%.2f -> %s (f1=%.4f, auc=%.4f)",
            row["split_train_ratio"],
            row["split_test_ratio"],
            row["model"],
            row["macro_f1"],
            row["roc_auc_macro_ovr"],
        )
    LOGGER.info(
        "Best overall: %s (f1=%.4f, auc=%.4f)",
        best_overall["model"],
        best_overall["macro_f1"],
        best_overall["roc_auc_macro_ovr"],
    )

    if not args.skip_submission:
        best_model_name = str(best_overall["model"])
        LOGGER.info("Training best model for submission: %s", best_model_name)
        best_model = train_best_model_on_full_train(
            model_name=best_model_name,
            config=MODEL_CONFIGS[best_model_name],
            images=images,
            labels=labels,
            args=args,
        )

        LOGGER.info("Loading test images from: %s", test_dir)
        test_paths = collect_test_paths(test_dir=test_dir, max_test_images=args.max_test_images)
        submission_path = output_dir / args.submission_file
        build_submission_csv(
            model=best_model,
            test_paths=test_paths,
            batch_size=args.batch_size,
            image_size=args.image_size,
            labels=CIFAR10_LABELS,
            output_path=submission_path,
            template_path=sample_submission,
        )
        LOGGER.info("Submission written to: %s (rows=%d)", submission_path.resolve(), len(test_paths))

    LOGGER.info("Artifacts written to: %s", output_dir.resolve())
