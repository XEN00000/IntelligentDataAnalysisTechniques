from __future__ import annotations

import logging

import tensorflow as tf

LOGGER = logging.getLogger("task3")


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), None)
    if not isinstance(level, int):
        raise ValueError(f"Unsupported log level: {level_name}")

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


class EpochMetricsLogger(tf.keras.callbacks.Callback):
    def __init__(self, run_name: str):
        super().__init__()
        self.run_name = run_name

    def on_train_begin(self, logs: dict[str, float] | None = None) -> None:
        epochs = self.params.get("epochs")
        steps = self.params.get("steps")
        LOGGER.info(
            "Training started [%s] (epochs=%s, steps_per_epoch=%s)",
            self.run_name,
            epochs,
            steps,
        )

    def on_epoch_end(self, epoch: int, logs: dict[str, float] | None = None) -> None:
        metrics = logs or {}
        metric_parts = [f"{key}={float(value):.4f}" for key, value in metrics.items()]
        LOGGER.info("Epoch %d finished [%s] %s", epoch + 1, self.run_name, " ".join(metric_parts))

    def on_train_end(self, logs: dict[str, float] | None = None) -> None:
        LOGGER.info("Training finished [%s]", self.run_name)
