from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import TypedDict


class OverfittingCheckConfig(TypedDict):
    seed: int
    val_ratio: float
    batch_size: int
    image_size: int
    learning_rate: float
    weights: str
    docker_image: str
    docker_gpus: str
    build_image_before_run: bool
    source_experiment_dir: str
    output_dir_name: str
    macro_f1_overfit_threshold: float


CONFIG: OverfittingCheckConfig = {
    "seed": 42,
    "val_ratio": 0.1,
    "batch_size": 64,
    "image_size": 160,
    "learning_rate": 0.001,
    "weights": "imagenet",
    "docker_image": "task3-image-benchmark",
    "docker_gpus": "all",
    "build_image_before_run": True,
    "source_experiment_dir": "split-impact-seed-42",
    "output_dir_name": "overfitting-check-seed-42",
    "macro_f1_overfit_threshold": 0.02,
}


def _experiment_tag(split_ratio: float) -> str:
    train_pct = int(round(split_ratio * 100))
    test_pct = 100 - train_pct
    return f"train{train_pct}_test{test_pct}"


def _read_summary_rows(summary_path: Path) -> list[dict[str, str]]:
    if not summary_path.exists():
        raise FileNotFoundError(f"Summary file not found: {summary_path}")

    with summary_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"Summary file has no rows: {summary_path}")
    return rows


def _resolve_weight_path(run_dir: Path, summary_row: dict[str, str]) -> Path:
    raw_weight_path = summary_row.get("weights_path", "").strip()
    if not raw_weight_path:
        raise ValueError(f"Missing weights_path in summary row: {summary_row}")

    weight_filename = Path(raw_weight_path).name
    host_weight_path = run_dir / "models" / weight_filename
    if not host_weight_path.exists():
        raise FileNotFoundError(f"Expected weight file not found: {host_weight_path}")
    return host_weight_path


def _to_container_path(outputs_root: Path, target_path: Path) -> str:
    relative = target_path.resolve().relative_to(outputs_root.resolve())
    return str(PurePosixPath("/app/outputs", *relative.parts))


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    outputs_root = (script_dir / "outputs").resolve()
    data_dir_host = (script_dir / "data" / "cifar-10").resolve()
    source_run_dir = outputs_root / CONFIG["source_experiment_dir"]
    summary_path = source_run_dir / "summary.csv"
    output_run_dir = outputs_root / CONFIG["output_dir_name"]
    output_run_dir.mkdir(parents=True, exist_ok=True)

    docker_image = CONFIG["docker_image"]
    if bool(CONFIG["build_image_before_run"]):
        build_command = ["docker", "build", "-t", docker_image, "."]
        print("Buduję obraz Docker:", " ".join(build_command))
        build_completed = subprocess.run(build_command, cwd=script_dir, check=False)
        if build_completed.returncode != 0:
            return build_completed.returncode

    summary_rows = _read_summary_rows(summary_path)
    summary_rows.sort(key=lambda row: (float(row["split_train_ratio"]), row["model"]))

    combined_results: list[dict[str, float | str | int | bool]] = []
    for index, row in enumerate(summary_rows, start=1):
        split_ratio = float(row["split_train_ratio"])
        model_name = row["model"].strip().lower()
        split_tag = _experiment_tag(split_ratio)

        weight_host_path = _resolve_weight_path(source_run_dir, row)
        weight_container_path = _to_container_path(outputs_root, weight_host_path)
        output_dir_container = str(PurePosixPath("/app/outputs", CONFIG["output_dir_name"]))

        app_args = [
            "python",
            "app.py",
            "--data-root",
            "/app/data/cifar-10",
            "--evaluate-model-path",
            weight_container_path,
            "--evaluate-model-name",
            model_name,
            "--evaluate-split",
            f"{split_ratio:g}",
            "--seed",
            str(CONFIG["seed"]),
            "--val-ratio",
            str(CONFIG["val_ratio"]),
            "--batch-size",
            str(CONFIG["batch_size"]),
            "--image-size",
            str(CONFIG["image_size"]),
            "--learning-rate",
            str(CONFIG["learning_rate"]),
            "--weights",
            str(CONFIG["weights"]),
            "--output-dir",
            output_dir_container,
            "--log-level",
            "INFO",
        ]
        command = [
            "docker",
            "run",
            "--rm",
            "--gpus",
            CONFIG["docker_gpus"],
            "--mount",
            f"type=bind,source={data_dir_host},target=/app/data/cifar-10",
            "--mount",
            f"type=bind,source={outputs_root},target=/app/outputs",
            docker_image,
            *app_args,
        ]

        print(
            f"[{index}/{len(summary_rows)}] Walidacja modelu={model_name} "
            f"split={split_ratio:g} wagi={weight_host_path.name}"
        )
        run_completed = subprocess.run(command, cwd=script_dir, check=False)
        if run_completed.returncode != 0:
            return run_completed.returncode

        validation_json = output_run_dir / f"validation_check_{model_name}_{split_tag}.json"
        if not validation_json.exists():
            raise FileNotFoundError(f"Expected validation result not found: {validation_json}")
        validation_metrics = json.loads(validation_json.read_text(encoding="utf-8"))

        test_macro_f1 = float(row["macro_f1"])
        validation_macro_f1 = float(validation_metrics["macro_f1"])
        test_accuracy = float(row["accuracy"])
        validation_accuracy = float(validation_metrics["accuracy"])

        macro_f1_gap = validation_macro_f1 - test_macro_f1
        accuracy_gap = validation_accuracy - test_accuracy
        overfit_warning = macro_f1_gap >= float(CONFIG["macro_f1_overfit_threshold"])

        combined_results.append(
            {
                "model": model_name,
                "split_train_ratio": split_ratio,
                "split_test_ratio": float(row["split_test_ratio"]),
                "weights_file": weight_host_path.name,
                "test_accuracy": test_accuracy,
                "validation_accuracy": validation_accuracy,
                "accuracy_gap_val_minus_test": accuracy_gap,
                "test_macro_f1": test_macro_f1,
                "validation_macro_f1": validation_macro_f1,
                "macro_f1_gap_val_minus_test": macro_f1_gap,
                "test_roc_auc_macro_ovr": float(row["roc_auc_macro_ovr"]),
                "validation_roc_auc_macro_ovr": float(validation_metrics["roc_auc_macro_ovr"]),
                "macro_f1_overfit_warning": overfit_warning,
                "overfit_threshold_used": float(CONFIG["macro_f1_overfit_threshold"]),
            }
        )

    report_csv = output_run_dir / "overfitting_validation_report.csv"
    report_json = output_run_dir / "overfitting_validation_report.json"
    csv_columns = [
        "model",
        "split_train_ratio",
        "split_test_ratio",
        "weights_file",
        "test_accuracy",
        "validation_accuracy",
        "accuracy_gap_val_minus_test",
        "test_macro_f1",
        "validation_macro_f1",
        "macro_f1_gap_val_minus_test",
        "test_roc_auc_macro_ovr",
        "validation_roc_auc_macro_ovr",
        "macro_f1_overfit_warning",
        "overfit_threshold_used",
    ]
    with report_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(combined_results)
    report_json.write_text(json.dumps(combined_results, indent=2), encoding="utf-8")

    print(f"Zapisano raport CSV: {report_csv}")
    print(f"Zapisano raport JSON: {report_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
