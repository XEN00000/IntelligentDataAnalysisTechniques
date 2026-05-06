from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    auc,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import label_binarize


CIFAR10_LABELS = [
    "airplane",
    "automobile",
    "bird",
    "cat",
    "deer",
    "dog",
    "frog",
    "horse",
    "ship",
    "truck",
]
LABEL_TO_INDEX = {label: index for index, label in enumerate(CIFAR10_LABELS)}


@dataclass(frozen=True)
class ModelConfig:
    builder: Callable[..., tf.keras.Model]
    preprocess: Callable[[tf.Tensor], tf.Tensor]


MODEL_CONFIGS: dict[str, ModelConfig] = {
    "mobilenetv2": ModelConfig(
        builder=tf.keras.applications.MobileNetV2,
        preprocess=tf.keras.applications.mobilenet_v2.preprocess_input,
    ),
    "efficientnetb0": ModelConfig(
        builder=tf.keras.applications.EfficientNetB0,
        preprocess=tf.keras.applications.efficientnet.preprocess_input,
    ),
    "resnet50": ModelConfig(
        builder=tf.keras.applications.ResNet50,
        preprocess=tf.keras.applications.resnet50.preprocess_input,
    ),
}


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


def setup_seed(seed: int) -> None:
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)


def resolve_dataset_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path | None]:
    data_root = Path(args.data_root)
    labels_csv = Path(args.labels_file) if args.labels_file else data_root / "trainLabels.csv"
    sample_submission = (
        Path(args.submission_template)
        if args.submission_template
        else (data_root / "sampleSubmission.csv")
    )

    if args.train_dir:
        train_dir = Path(args.train_dir)
    else:
        train_candidates = [data_root / "train" / "train", data_root / "train"]
        train_dir = next((path for path in train_candidates if path.exists()), None)
        if train_dir is None:
            raise FileNotFoundError(
                "Training image folder not found. Expected one of: "
                f"{train_candidates[0]} or {train_candidates[1]}. "
                "Use --train-dir to point to the correct folder."
            )

    if args.test_dir:
        test_dir = Path(args.test_dir)
    else:
        test_candidates = [data_root / "test" / "test", data_root / "test"]
        test_dir = next((path for path in test_candidates if path.exists()), None)
        if test_dir is None:
            raise FileNotFoundError(
                "Test image folder not found. Expected one of: "
                f"{test_candidates[0]} or {test_candidates[1]}. "
                "Use --test-dir to point to the correct folder."
            )

    if not labels_csv.exists():
        raise FileNotFoundError(f"Labels file not found: {labels_csv}")
    if sample_submission is not None and not sample_submission.exists():
        sample_submission = None

    return train_dir, test_dir, labels_csv, sample_submission


def load_training_frame(
    labels_csv: Path,
    train_dir: Path,
    max_samples: int | None,
    seed: int,
) -> pd.DataFrame:
    labels_df = pd.read_csv(labels_csv)
    required_cols = {"id", "label"}
    if not required_cols.issubset(labels_df.columns):
        raise ValueError(f"{labels_csv} must contain columns: {sorted(required_cols)}")

    labels_df = labels_df[["id", "label"]].copy()
    labels_df["id"] = pd.to_numeric(labels_df["id"], errors="raise").astype(int)
    labels_df["label"] = labels_df["label"].astype(str).str.strip().str.lower()
    labels_df = labels_df.sort_values("id").reset_index(drop=True)

    unknown = sorted(set(labels_df["label"]) - set(CIFAR10_LABELS))
    if unknown:
        raise ValueError(f"Unknown labels in {labels_csv}: {unknown}")

    labels_df["image_path"] = labels_df["id"].map(lambda image_id: str(train_dir / f"{image_id}.png"))
    missing = [path for path in labels_df["image_path"] if not Path(path).exists()]
    if missing:
        preview = ", ".join(missing[:5])
        raise FileNotFoundError(
            f"Missing {len(missing)} training images referenced by trainLabels.csv. Examples: {preview}"
        )

    if max_samples is not None and 0 < max_samples < len(labels_df):
        sampled_idx, _ = train_test_split(
            labels_df.index.to_numpy(),
            train_size=max_samples,
            stratify=labels_df["label"].to_numpy(),
            random_state=seed,
        )
        labels_df = labels_df.loc[sampled_idx].sort_values("id").reset_index(drop=True)

    return labels_df


def read_png_as_array(path: Path) -> np.ndarray:
    image_bytes = tf.io.read_file(str(path))
    decoded = tf.io.decode_png(image_bytes, channels=3)
    image = decoded.numpy()
    if image.shape != (32, 32, 3):
        resized = tf.image.resize(image, (32, 32))
        image = tf.cast(resized, tf.uint8).numpy()
    return image


def load_train_arrays(training_frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    image_paths = training_frame["image_path"].to_list()
    labels = training_frame["label"].map(LABEL_TO_INDEX).to_numpy(dtype=np.int32)

    images = np.empty((len(image_paths), 32, 32, 3), dtype=np.uint8)
    for idx, image_path in enumerate(image_paths):
        images[idx] = read_png_as_array(Path(image_path))

    return images, labels


def create_dataset(
    images: np.ndarray,
    labels: np.ndarray,
    batch_size: int,
    image_size: int,
    training: bool,
    seed: int,
) -> tf.data.Dataset:
    ds = tf.data.Dataset.from_tensor_slices((images, labels))
    if training:
        ds = ds.shuffle(buffer_size=len(images), seed=seed, reshuffle_each_iteration=True)

    def preprocess(image: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        resized = tf.image.resize(image, (image_size, image_size))
        return tf.cast(resized, tf.float32), label

    ds = ds.map(preprocess, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return ds


def create_path_dataset(
    image_paths: list[Path],
    batch_size: int,
    image_size: int,
) -> tf.data.Dataset:
    path_values = [str(path) for path in image_paths]
    ds = tf.data.Dataset.from_tensor_slices(path_values)

    def preprocess(path: tf.Tensor) -> tf.Tensor:
        image_bytes = tf.io.read_file(path)
        image = tf.io.decode_png(image_bytes, channels=3)
        image = tf.image.resize(image, (image_size, image_size))
        return tf.cast(image, tf.float32)

    ds = ds.map(preprocess, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return ds


def build_model(
    model_name: str,
    model_config: ModelConfig,
    num_classes: int,
    image_size: int,
    learning_rate: float,
    weights: str,
) -> tf.keras.Model:
    base_model = model_config.builder(
        include_top=False,
        weights=None if weights == "none" else weights,
        input_shape=(image_size, image_size, 3),
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=(image_size, image_size, 3), name="image")
    x = tf.keras.layers.Lambda(model_config.preprocess, name="preprocess")(inputs)
    x = tf.keras.layers.RandomFlip("horizontal")(x)
    x = tf.keras.layers.RandomRotation(0.05)(x)
    x = base_model(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)

    model = tf.keras.Model(inputs=inputs, outputs=outputs, name=model_name)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


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


def experiment_tag(train_ratio: float) -> str:
    train_pct = int(round(train_ratio * 100))
    test_pct = 100 - train_pct
    return f"train{train_pct}_test{test_pct}"


def ensure_class_coverage(y: np.ndarray, split_name: str, expected_classes: int) -> None:
    covered = np.unique(y).size
    if covered != expected_classes:
        raise ValueError(
            f"{split_name} has {covered}/{expected_classes} classes. "
            "Increase --max-samples or change split ratios to keep all classes represented."
        )


def run_experiment(
    model_name: str,
    config: ModelConfig,
    split_ratio: float,
    x_train: np.ndarray,
    x_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    labels: list[str],
    args: argparse.Namespace,
    plots_dir: Path,
    models_dir: Path,
) -> dict[str, float | str | int]:
    split_tag = experiment_tag(split_ratio)
    ensure_class_coverage(y=y_test, split_name="test split", expected_classes=len(labels))

    x_train_fit, x_val, y_train_fit, y_val = train_test_split(
        x_train,
        y_train,
        test_size=args.val_ratio,
        stratify=y_train,
        random_state=args.seed,
    )
    ensure_class_coverage(y=y_train_fit, split_name="train split", expected_classes=len(labels))
    ensure_class_coverage(y=y_val, split_name="validation split", expected_classes=len(labels))

    model = build_model(
        model_name=model_name,
        model_config=config,
        num_classes=len(labels),
        image_size=args.image_size,
        learning_rate=args.learning_rate,
        weights=args.weights,
    )

    train_ds = create_dataset(
        images=x_train_fit,
        labels=y_train_fit,
        batch_size=args.batch_size,
        image_size=args.image_size,
        training=True,
        seed=args.seed,
    )
    val_ds = create_dataset(
        images=x_val,
        labels=y_val,
        batch_size=args.batch_size,
        image_size=args.image_size,
        training=False,
        seed=args.seed,
    )
    test_ds = create_dataset(
        images=x_test,
        labels=y_test,
        batch_size=args.batch_size,
        image_size=args.image_size,
        training=False,
        seed=args.seed,
    )

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=args.patience,
            restore_best_weights=True,
        )
    ]

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=callbacks,
        verbose=2,
    )

    y_prob = model.predict(test_ds, verbose=0)
    y_pred = np.argmax(y_prob, axis=1)

    accuracy = float(accuracy_score(y_test, y_pred))
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test,
        y_pred,
        average="macro",
        zero_division=0,
    )

    y_true_bin = label_binarize(y_test, classes=np.arange(len(labels)))
    roc_auc_macro = float(roc_auc_score(y_true_bin, y_prob, average="macro", multi_class="ovr"))
    roc_auc_micro = save_roc_plot(
        y_true_bin=y_true_bin,
        y_prob=y_prob,
        title=f"ROC curve: {model_name} ({split_tag})",
        output_path=plots_dir / f"roc_{model_name}_{split_tag}.png",
    )

    cm = confusion_matrix(y_test, y_pred)
    save_confusion_matrix_plot(
        cm=cm,
        labels=labels,
        title=f"Confusion matrix: {model_name} ({split_tag})",
        output_path=plots_dir / f"cm_{model_name}_{split_tag}.png",
    )

    save_prediction_preview(
        images=x_test,
        y_true=y_test,
        y_pred=y_pred,
        labels=labels,
        output_path=plots_dir / f"predictions_{model_name}_{split_tag}.png",
        sample_count=args.preview_samples,
        seed=args.seed,
    )

    if args.save_models:
        model.save(models_dir / f"{model_name}_{split_tag}.keras")

    return {
        "model": model_name,
        "split_train_ratio": split_ratio,
        "split_test_ratio": 1.0 - split_ratio,
        "train_samples": int(len(x_train_fit)),
        "validation_samples": int(len(x_val)),
        "test_samples": int(len(x_test)),
        "epochs_trained": int(len(history.history["loss"])),
        "accuracy": accuracy,
        "macro_precision": float(precision),
        "macro_recall": float(recall),
        "macro_f1": float(f1),
        "roc_auc_macro_ovr": roc_auc_macro,
        "roc_auc_micro": roc_auc_micro,
    }


def collect_test_paths(test_dir: Path, max_test_images: int | None) -> list[Path]:
    paths = list(test_dir.glob("*.png"))
    if not paths:
        raise FileNotFoundError(f"No PNG files found in test folder: {test_dir}")

    def sort_key(path: Path) -> tuple[int, int | str]:
        stem = path.stem
        if stem.isdigit():
            return (0, int(stem))
        return (1, stem)

    paths.sort(key=sort_key)
    if max_test_images is not None and 0 < max_test_images < len(paths):
        paths = paths[:max_test_images]
    return paths


def train_best_model_on_full_train(
    model_name: str,
    config: ModelConfig,
    images: np.ndarray,
    labels: np.ndarray,
    args: argparse.Namespace,
) -> tf.keras.Model:
    x_train_fit, x_val, y_train_fit, y_val = train_test_split(
        images,
        labels,
        test_size=args.val_ratio,
        stratify=labels,
        random_state=args.seed,
    )
    ensure_class_coverage(y=y_train_fit, split_name="submission train split", expected_classes=len(CIFAR10_LABELS))
    ensure_class_coverage(y=y_val, split_name="submission validation split", expected_classes=len(CIFAR10_LABELS))

    model = build_model(
        model_name=model_name,
        model_config=config,
        num_classes=len(CIFAR10_LABELS),
        image_size=args.image_size,
        learning_rate=args.learning_rate,
        weights=args.weights,
    )

    train_ds = create_dataset(
        images=x_train_fit,
        labels=y_train_fit,
        batch_size=args.batch_size,
        image_size=args.image_size,
        training=True,
        seed=args.seed,
    )
    val_ds = create_dataset(
        images=x_val,
        labels=y_val,
        batch_size=args.batch_size,
        image_size=args.image_size,
        training=False,
        seed=args.seed,
    )

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=args.patience,
            restore_best_weights=True,
        )
    ]
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=callbacks,
        verbose=2,
    )
    return model


def build_submission_csv(
    model: tf.keras.Model,
    test_paths: list[Path],
    args: argparse.Namespace,
    labels: list[str],
    output_path: Path,
    template_path: Path | None,
) -> None:
    test_ds = create_path_dataset(
        image_paths=test_paths,
        batch_size=args.batch_size,
        image_size=args.image_size,
    )
    y_prob = model.predict(test_ds, verbose=0)
    y_pred = np.argmax(y_prob, axis=1)

    prediction_df = pd.DataFrame(
        {
            "id": [int(path.stem) for path in test_paths],
            "label": [labels[int(index)] for index in y_pred],
        }
    )

    if template_path is not None:
        template = pd.read_csv(template_path)
        if not {"id", "label"}.issubset(template.columns):
            raise ValueError(f"{template_path} must contain 'id' and 'label' columns.")
        submission = template[["id"]].merge(prediction_df, how="left", on="id")
        if submission["label"].isna().any():
            missing_count = int(submission["label"].isna().sum())
            raise ValueError(
                f"Submission has {missing_count} missing predictions. "
                "Do not use --max-test-images when creating final submission."
            )
    else:
        submission = prediction_df.sort_values("id")

    submission.to_csv(output_path, index=False)


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_seed(args.seed)

    model_names = parse_csv_list(args.models)
    if not model_names:
        raise ValueError("No models selected. Pass at least one value via --models.")
    invalid_models = [name for name in model_names if name not in MODEL_CONFIGS]
    if invalid_models:
        allowed = ", ".join(MODEL_CONFIGS.keys())
        raise ValueError(f"Unknown models: {invalid_models}. Allowed: {allowed}")

    split_ratios = parse_split_ratios(args.splits)
    if args.val_ratio <= 0.0 or args.val_ratio >= 0.5:
        raise ValueError("Validation ratio must be between 0 and 0.5.")

    train_dir, test_dir, labels_csv, sample_submission = resolve_dataset_paths(args)

    output_dir = Path(args.output_dir)
    plots_dir = output_dir / "plots"
    models_dir = output_dir / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)
    if args.save_models:
        models_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading training labels from: {labels_csv}")
    print(f"Loading training images from: {train_dir}")
    training_frame = load_training_frame(
        labels_csv=labels_csv,
        train_dir=train_dir,
        max_samples=args.max_samples,
        seed=args.seed,
    )
    images, labels = load_train_arrays(training_frame)

    all_results: list[dict[str, float | str | int]] = []
    for split_ratio in split_ratios:
        x_train, x_test, y_train, y_test = train_test_split(
            images,
            labels,
            train_size=split_ratio,
            stratify=labels,
            random_state=args.seed,
        )

        for model_name in model_names:
            print(f"\n>>> Training {model_name} for split {split_ratio:.2f}/{1.0 - split_ratio:.2f}")
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
            print(
                f"Result: acc={result['accuracy']:.4f} "
                f"f1={result['macro_f1']:.4f} auc={result['roc_auc_macro_ovr']:.4f}"
            )

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
            default=lambda value: float(value) if isinstance(value, (np.floating, np.integer)) else str(value),
        ),
        encoding="utf-8",
    )

    print("\n=== Best model per split (macro F1) ===")
    for _, row in best_by_split.iterrows():
        print(
            f"split={row['split_train_ratio']:.2f}/{row['split_test_ratio']:.2f} "
            f"-> {row['model']} (f1={row['macro_f1']:.4f}, auc={row['roc_auc_macro_ovr']:.4f})"
        )
    print(
        f"\nBest overall: {best_overall['model']} "
        f"(f1={best_overall['macro_f1']:.4f}, auc={best_overall['roc_auc_macro_ovr']:.4f})"
    )

    if not args.skip_submission:
        best_model_name = str(best_overall["model"])
        print(f"\nTraining best model for submission: {best_model_name}")
        best_model = train_best_model_on_full_train(
            model_name=best_model_name,
            config=MODEL_CONFIGS[best_model_name],
            images=images,
            labels=labels,
            args=args,
        )

        print(f"Loading test images from: {test_dir}")
        test_paths = collect_test_paths(test_dir=test_dir, max_test_images=args.max_test_images)
        submission_path = output_dir / args.submission_file
        build_submission_csv(
            model=best_model,
            test_paths=test_paths,
            args=args,
            labels=CIFAR10_LABELS,
            output_path=submission_path,
            template_path=sample_submission,
        )
        print(f"Submission written to: {submission_path.resolve()} (rows={len(test_paths)})")

    print(f"\nArtifacts written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
