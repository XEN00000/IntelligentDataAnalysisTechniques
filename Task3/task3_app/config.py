from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import tensorflow as tf

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
