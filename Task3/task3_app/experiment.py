from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import label_binarize

from .config import CIFAR10_LABELS, ModelConfig
from .data import create_dataset
from .logging_utils import EpochMetricsLogger, LOGGER
from .modeling import build_model
from .visualization import (
    save_confusion_matrix_plot,
    save_prediction_preview,
    save_roc_plot,
)


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
    run_name = f"{model_name}/{split_tag}"
    LOGGER.info("Starting experiment [%s]", run_name)
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
        ),
        EpochMetricsLogger(run_name=run_name),
    ]

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=callbacks,
        verbose=0,
    )

    LOGGER.info("Evaluating model [%s] on test split", run_name)
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
        model_path = models_dir / f"{model_name}_{split_tag}.keras"
        model.save(model_path)
        LOGGER.info("Saved model [%s] to %s", run_name, model_path)

    LOGGER.info(
        "Completed experiment [%s]: acc=%.4f f1=%.4f auc=%.4f",
        run_name,
        accuracy,
        float(f1),
        roc_auc_macro,
    )

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


def train_best_model_on_full_train(
    model_name: str,
    config: ModelConfig,
    images: np.ndarray,
    labels: np.ndarray,
    args: argparse.Namespace,
) -> tf.keras.Model:
    LOGGER.info("Training best model on full labeled training data [%s]", model_name)
    x_train_fit, x_val, y_train_fit, y_val = train_test_split(
        images,
        labels,
        test_size=args.val_ratio,
        stratify=labels,
        random_state=args.seed,
    )
    ensure_class_coverage(
        y=y_train_fit,
        split_name="submission train split",
        expected_classes=len(CIFAR10_LABELS),
    )
    ensure_class_coverage(
        y=y_val,
        split_name="submission validation split",
        expected_classes=len(CIFAR10_LABELS),
    )

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
        ),
        EpochMetricsLogger(run_name=f"{model_name}/submission"),
    ]
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.epochs,
        callbacks=callbacks,
        verbose=0,
    )
    LOGGER.info("Finished training best model for submission [%s]", model_name)
    return model
