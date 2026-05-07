from __future__ import annotations

import tensorflow as tf

from .config import ModelConfig


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
