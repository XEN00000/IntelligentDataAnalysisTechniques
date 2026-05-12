from __future__ import annotations

import subprocess
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
    docker_image: str
    docker_gpus: str
    build_image_before_run: bool


CONFIG: ExperimentConfig = {
    "seed": 42,
    "models": ["mobilenetv2", "efficientnetb0", "resnet50"],
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
    "docker_image": "task3-image-benchmark",
    "docker_gpus": "all",
    "build_image_before_run": False,
}


def build_splits_csv(config: ExperimentConfig) -> str:
    splits = sorted(set(config["normal_splits"] + config["extreme_splits"]))
    return ",".join(f"{split:g}" for split in splits)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    splits_csv = build_splits_csv(CONFIG)
    seed = CONFIG["seed"]
    models = ",".join(CONFIG["models"])
    output_dir = f"/app/outputs/split-impact-seed-{seed}"
    docker_image = CONFIG["docker_image"]
    data_dir_host = (script_dir / "data" / "cifar-10").resolve()
    outputs_dir_host = (script_dir / "outputs").resolve()
    outputs_dir_host.mkdir(parents=True, exist_ok=True)

    app_args = [
        "python",
        "app.py",
        "--data-root",
        "/app/data/cifar-10",
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
        app_args.append("--save-models")

    if bool(CONFIG["build_image_before_run"]):
        build_command = ["docker", "build", "-t", docker_image, "."]
        print("Buduję obraz Docker:", " ".join(build_command))
        build_completed = subprocess.run(build_command, cwd=script_dir, check=False)
        if build_completed.returncode != 0:
            return build_completed.returncode

    command = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        CONFIG["docker_gpus"],
        "--mount",
        f"type=bind,source={data_dir_host},target=/app/data/cifar-10",
        "--mount",
        f"type=bind,source={outputs_dir_host},target=/app/outputs",
        docker_image,
        *app_args,
    ]

    print(f"Uruchamiam eksperyment split-impact w Docker z seed={seed}")
    print(f"Modele: {models}")
    print(f"Splity (normalne + skrajne): {splits_csv}")
    print("Polecenie:", " ".join(command))
    completed = subprocess.run(command, cwd=script_dir, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
