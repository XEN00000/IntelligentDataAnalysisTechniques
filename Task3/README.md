# Task 3 - CIFAR-10 benchmark + submission app

This app implements the **grade 5 scope** from `Zadanie 3.txt` on unpacked CIFAR-10 PNG files:

1. compares at least 3 models (`MobileNetV2`, `EfficientNetB0`, `ResNet50`),
2. evaluates multiple train/test split ratios,
3. reports confusion matrix, accuracy, precision, recall, F1,
4. reports and plots ROC/AUC,
5. generates a submission file with predictions for all test images.

## Expected dataset layout

After unpacking `train.7z` and `test.7z`, the default expected structure is:

```text
Task3\data\cifar-10\
  trainLabels.csv
  sampleSubmission.csv
  train\train\1.png
  train\train\2.png
  ...
  test\test\1.png
  test\test\2.png
  ...
```

If your folders differ, pass `--train-dir`, `--test-dir`, or `--labels-file`.

## How to run (local)

```powershell
cd Task3
pip install -r requirements.txt
python app.py
```

This default run:

1. trains/evaluates 3 models for split ratios `0.7,0.8,0.85`,
2. saves metric summaries and plots,
3. retrains the best model and creates `outputs\submission_best.csv`.

## Code architecture

The app is now split into focused modules under `Task3\task3_app\`:

- `cli.py` - CLI argument parsing and split/model list parsing.
- `config.py` - model definitions and CIFAR-10 label constants.
- `logging_utils.py` - logging setup and training epoch callback.
- `data.py` - dataset path resolution, data loading, and TF dataset builders.
- `modeling.py` - transfer-learning model construction.
- `visualization.py` - confusion matrix, ROC, and prediction preview plots.
- `experiment.py` - training/evaluation experiment flow.
- `submission.py` - submission CSV generation.
- `pipeline.py` - top-level orchestration previously contained in `app.py`.

`app.py` remains the entrypoint and now delegates to `task3_app.pipeline.main()`.

### Useful options

```powershell
python app.py `
  --data-root "data/cifar-10" `
  --models "mobilenetv2,efficientnetb0,resnet50" `
  --splits "0.7,0.8,0.85" `
  --epochs 4 `
  --max-samples 20000
```

Fast debug run (no final submission):

```powershell
python app.py --max-samples 5000 --splits 0.8 --skip-submission
```

Show more/less app progress logs:

```powershell
python app.py --log-level INFO
python app.py --log-level DEBUG
```

## Output files

All outputs are written to `Task3\outputs\`:

- `summary.csv`, `summary.json` - all experiments,
- `best_models_by_split.csv` - best model per split,
- `best_overall.json` - top model overall,
- `submission_best.csv` - predicted labels for test images,
- `plots\` - ROC plots, confusion matrices, and prediction previews.

## Docker

GPU Docker requires NVIDIA drivers + NVIDIA Container Toolkit installed on host.

Build:

```powershell
cd Task3
docker build -t task3-image-benchmark .
```

Run with mounted dataset and outputs:

```powershell
docker run --rm --gpus all `
  -v "${PWD}\data\cifar-10:/app/data/cifar-10" `
  -v "${PWD}\outputs:/app/outputs" `
  task3-image-benchmark
```

The Docker image runs with `--log-level INFO` by default.

Custom example:

```powershell
docker run --rm --gpus all `
  -v "${PWD}\data\cifar-10:/app/data/cifar-10" `
  -v "${PWD}\outputs:/app/outputs" `
  task3-image-benchmark `
  python app.py --splits 0.8 --epochs 3 --max-samples 15000 --log-level INFO
```

## Design decisions

1. **Use unpacked PNG dataset** (`trainLabels.csv` + `train`/`test` folders) so the app matches the provided competition-like data format.
2. **Use 3 transfer-learning backbones** to satisfy the grade-5 requirement and compare architectures with different efficiency/accuracy tradeoffs.
3. **Evaluate via configurable splits on labeled training data** because the public test set has no ground-truth labels.
4. **Generate full submission CSV** (including 300k test images) with the best-performing model from evaluation.



# Run with GPU
```powershell
docker run --rm --gpus all `
   --mount type=bind,source="${PWD}\data\cifar-10",target=/app/data/cifar-10 `
   --mount type=bind,source="${PWD}\outputs",target=/app/outputs `
   task3-image-benchmark
```

  # Dataset
  https://www.kaggle.com/competitions/cifar-10/data
