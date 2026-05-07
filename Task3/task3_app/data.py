from __future__ import annotations

import argparse
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split

from .config import CIFAR10_LABELS, LABEL_TO_INDEX
from .logging_utils import LOGGER


def setup_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    os.environ["TF_DETERMINISTIC_OPS"] = "1"
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)
    tf.config.experimental.enable_op_determinism()


def resolve_dataset_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path | None]:
    data_root = Path(args.data_root)
    labels_csv = Path(args.labels_file) if args.labels_file else data_root / "trainLabels.csv"
    sample_submission = (
        Path(args.submission_template) if args.submission_template else (data_root / "sampleSubmission.csv")
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
        LOGGER.warning("Submission template not found at %s. Will write raw id/label CSV.", sample_submission)
        sample_submission = None

    return train_dir, test_dir, labels_csv, sample_submission


def load_training_frame(
    labels_csv: Path,
    train_dir: Path,
    max_samples: int | None,
    seed: int,
) -> pd.DataFrame:
    labels_df = pd.read_csv(labels_csv)
    LOGGER.info("Loaded %d label rows from %s", len(labels_df), labels_csv)
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

    original_count = len(labels_df)
    if max_samples is not None and 0 < max_samples < len(labels_df):
        sampled_idx, _ = train_test_split(
            labels_df.index.to_numpy(),
            train_size=max_samples,
            stratify=labels_df["label"].to_numpy(),
            random_state=seed,
        )
        labels_df = labels_df.loc[sampled_idx].sort_values("id").reset_index(drop=True)
        LOGGER.info("Sampled training rows: %d (from %d)", len(labels_df), original_count)
    else:
        LOGGER.info("Using full training set: %d rows", original_count)

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
    LOGGER.info("Reading %d training images into memory", len(image_paths))
    for idx, image_path in enumerate(image_paths):
        images[idx] = read_png_as_array(Path(image_path))
        loaded = idx + 1
        if loaded % 5000 == 0 or loaded == len(image_paths):
            LOGGER.info("Loaded training images: %d/%d", loaded, len(image_paths))

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
    options = tf.data.Options()
    options.experimental_deterministic = True
    ds = ds.with_options(options)

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
    options = tf.data.Options()
    options.experimental_deterministic = True
    ds = ds.with_options(options)

    def preprocess(path: tf.Tensor) -> tf.Tensor:
        image_bytes = tf.io.read_file(path)
        image = tf.io.decode_png(image_bytes, channels=3)
        image = tf.image.resize(image, (image_size, image_size))
        return tf.cast(image, tf.float32)

    ds = ds.map(preprocess, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return ds


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
        LOGGER.info("Using subset of test images: %d", len(paths))
    else:
        LOGGER.info("Collected test images: %d", len(paths))
    return paths
