from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TypedDict


class ExperimentConfig(TypedDict):
    seed: int
    models: list[str]
    normal_splits: list[float]
    extreme_splits: list[float]
    epochs: int
    patience: int
    batch_size: int
    image_size: int
    learning_rate: float
    weights: str
    val_ratio: float
    save_models: bool


CONFIG: ExperimentConfig = {
    "seed": 42,
    "models": ["mobilenetv2"],
    "normal_splits": [0.5, 0.7, 0.8, 0.85],
    "extreme_splits": [0.05, 0.1, 0.2, 0.9, 0.95],
    "epochs": 4,
    "patience": 2,
    "batch_size": 64,
    "image_size": 160,
    "learning_rate": 0.001,
    "weights": "imagenet",
    "val_ratio": 0.1,
    "save_models": False,
}


def build_splits_csv(config: ExperimentConfig) -> str:
    splits = sorted(set(config["normal_splits"] + config["extreme_splits"]))
    return ",".join(f"{split:g}" for split in splits)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    app_path = script_dir / "app.py"
    splits_csv = build_splits_csv(CONFIG)
    seed = CONFIG["seed"]
    models = ",".join(CONFIG["models"])
    output_dir = f"outputs\\split-impact-seed-{seed}"

    command = [
        sys.executable,
        str(app_path),
        "--models",
        models,
        "--splits",
        splits_csv,
        "--epochs",
        str(CONFIG["epochs"]),
        "--patience",
        str(CONFIG["patience"]),
        "--batch-size",
        str(CONFIG["batch_size"]),
        "--image-size",
        str(CONFIG["image_size"]),
        "--learning-rate",
        str(CONFIG["learning_rate"]),
        "--weights",
        str(CONFIG["weights"]),
        "--val-ratio",
        str(CONFIG["val_ratio"]),
        "--seed",
        str(seed),
        "--skip-submission",
        "--output-dir",
        output_dir,
        "--log-level",
        "INFO",
    ]

    if bool(CONFIG["save_models"]):
        command.append("--save-models")

    print(f"Uruchamiam eksperyment split-impact z seed={seed}")
    print(f"Splity (normalne + skrajne): {splits_csv}")
    print("Polecenie:", " ".join(command))
    completed = subprocess.run(command, cwd=script_dir, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
