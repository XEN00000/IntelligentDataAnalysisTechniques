from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

from .data import create_path_dataset
from .logging_utils import LOGGER


def build_submission_csv(
    model: tf.keras.Model,
    test_paths: list[Path],
    batch_size: int,
    image_size: int,
    labels: list[str],
    output_path: Path,
    template_path: Path | None,
) -> None:
    LOGGER.info("Generating predictions for submission (images=%d)", len(test_paths))
    test_ds = create_path_dataset(
        image_paths=test_paths,
        batch_size=batch_size,
        image_size=image_size,
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
    LOGGER.info("Saved submission CSV to %s (rows=%d)", output_path, len(submission))
