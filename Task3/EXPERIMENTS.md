# Experiment parameter matrix

This file collects experiment setups (usual + edge cases) and result templates.

## Experiment 01 - How many training images are needed to avoid overtraining?

**Goal:** find the smallest training subset size (`--max-samples`) that keeps generalization stable and avoids clear overtraining.

### Fixed parameters for this experiment

| Parameter | Value |
|---|---|
| `--models` | `mobilenetv2` |
| `--splits` | `0.8` |
| `--epochs` | `12` |
| `--patience` | `3` |
| `--batch-size` | `64` |
| `--image-size` | `160` |
| `--learning-rate` | `0.001` |
| `--weights` | `imagenet` |
| `--val-ratio` | `0.1` |
| `--seed` | `42` |
| `--skip-submission` | enabled |
| `--log-level` | `INFO` |

### Cases (usual + edge)

| Run ID | Case type | `--max-samples` | Why this case | Expected behavior |
|---|---|---:|---|---|
| E01-EDGE-1 | Edge (very low data) | 500 | Stress-test under extreme data scarcity | Strong overtraining, unstable metrics |
| E01-U1 | Usual | 2,000 | Small but practical quick-run subset | Visible overtraining, lower macro-F1 |
| E01-U2 | Usual | 5,000 | Common debug-size benchmark | Better stability, still some overtraining |
| E01-U3 | Usual | 10,000 | Mid-size baseline | Improved generalization, lower train/val gap |
| E01-U4 | Usual | 20,000 | Larger practical subset | More stable validation/test metrics |
| E01-U5 | Usual | 35,000 | Near-full training budget | Small overtraining gap, diminishing returns |
| E01-EDGE-2 | Edge (full data) | all samples (omit flag) | Upper bound for this setup | Best generalization, longest runtime |

### Run command templates

Python:

```powershell
python app.py --models mobilenetv2 --splits 0.8 --epochs 12 --patience 3 --batch-size 64 --image-size 160 --learning-rate 0.001 --weights imagenet --val-ratio 0.1 --seed 42 --skip-submission --log-level INFO --max-samples <VALUE>
```

Docker:

```powershell
docker run --rm --gpus all `
  --mount type=bind,source="${PWD}\data\cifar-10",target=/app/data/cifar-10 `
  --mount type=bind,source="${PWD}\outputs",target=/app/outputs `
  task3-image-benchmark `
  python app.py --models mobilenetv2 --splits 0.8 --epochs 12 --patience 3 --batch-size 64 --image-size 160 --learning-rate 0.001 --weights imagenet --val-ratio 0.1 --seed 42 --skip-submission --log-level INFO --max-samples <VALUE>
```

For `E01-EDGE-2` (full data), remove `--max-samples`.

### Result table (fill after runs)

| Run ID | max-samples | Final train acc | Final val acc | Train-val gap | Test accuracy | Macro-F1 | Overtraining? (Y/N) | Notes |
|---|---:|---:|---:|---:|---:|---:|---|---|
| E01-EDGE-1 | 500 |  |  |  |  |  |  |  |
| E01-U1 | 2,000 |  |  |  |  |  |  |  |
| E01-U2 | 5,000 |  |  |  |  |  |  |  |
| E01-U3 | 10,000 |  |  |  |  |  |  |  |
| E01-U4 | 20,000 |  |  |  |  |  |  |  |
| E01-U5 | 35,000 |  |  |  |  |  |  |  |
| E01-EDGE-2 | all |  |  |  |  |  |  |  |

### Decision rule

Pick the **smallest** `--max-samples` where:

1. train-val gap is consistently small (target around `<= 0.05`),
2. macro-F1 is close to the best run (for example within ~1 percentage point),
3. no clear validation degradation pattern appears across epochs.
