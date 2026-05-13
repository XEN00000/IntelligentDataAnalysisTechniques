# Task 3 - CIFAR-10 benchmark + submission app

This app implements the grade-5 scope from `Zadanie 3.txt` on unpacked CIFAR-10 PNG files:

1. compares at least 3 models (`mobilenetv2`, `efficientnetb0`, `resnet50`),
2. evaluates multiple train/test split ratios,
3. reports confusion matrix, accuracy, precision, recall, F1,
4. reports and plots ROC/AUC,
5. generates a submission CSV for test images.

## Expected dataset layout

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

If your layout differs, use `--train-dir`, `--test-dir`, `--labels-file`, and/or `--submission-template`.

## Code architecture

`Task3\task3_app\` is split by responsibility:

- `cli.py` - CLI parsing, validation, and selection helpers.
- `config.py` - labels and model definitions.
- `logging_utils.py` - logging setup and training callback.
- `data.py` - seed setup, dataset path resolution, loading, TF dataset builders.
- `modeling.py` - transfer-learning model construction.
- `visualization.py` - confusion matrix, ROC, and preview plots.
- `experiment.py` - experiment training/evaluation flow.
- `submission.py` - submission CSV generation.
- `pipeline.py` - top-level orchestration.

`app.py` is the entrypoint and calls `task3_app.pipeline.main()`.

## Reproducibility (seed)

Use `--seed` to keep dataset sampling/shuffling and train/test splits reproducible across runs:

```powershell
python app.py --seed 42
```

The same seed value can be passed in Docker (examples below).

## Python usage

Install:

```powershell
cd Task3
pip install -r requirements.txt
```

Default run:

```powershell
python app.py
```

Deterministic debug run (fast):

```powershell
python app.py --seed 42 --max-samples 5000 --splits 0.8 --skip-submission
```

Validation check for a trained model (on reconstructed validation split):

```powershell
python app.py `
  --evaluate-model-path "outputs\models\resnet50_train90_test10.weights.h5" `
  --evaluate-model-name resnet50 `
  --evaluate-split 0.9 `
  --seed 42 `
  --val-ratio 0.1 `
  --weights imagenet `
  --output-dir "outputs"
```

If filename follows `<model>_trainXX_testYY.weights.h5` (or `.keras`), model name and split can be inferred.

Python launcher for split-impact experiment in Docker (normal + extreme split values, fixed seed):

```powershell
cd Task3
python run_split_impact_experiment.py
```

Launcher uses a simple `CONFIG` dictionary in `run_split_impact_experiment.py` (without CLI arguments).
Default split set in the script:

- models: `mobilenetv2, efficientnetb0, resnet50`
- normal: `0.5, 0.7, 0.8, 0.85`
- extreme: `0.05, 0.1, 0.2, 0.9, 0.95`

Before first run, build the Docker image:

```powershell
cd Task3
docker build -t task3-image-benchmark .
```

Custom full run:

```powershell
python app.py `
  --data-root "data/cifar-10" `
  --models "mobilenetv2,efficientnetb0,resnet50" `
  --splits "0.7,0.8,0.85" `
  --epochs 4 `
  --batch-size 64 `
  --image-size 160 `
  --learning-rate 0.001 `
  --patience 2 `
  --weights imagenet `
  --val-ratio 0.1 `
  --seed 42 `
  --output-dir "outputs"
```

Show all help text:

```powershell
python app.py --help
```

## Docker usage (GPU)

Requirements on host:

- NVIDIA GPU driver,
- NVIDIA Container Toolkit,
- Docker with GPU support.

Build image:

```powershell
cd Task3
docker build -t task3-image-benchmark .
```

Default run (uses image CMD: `python app.py --log-level INFO`):

```powershell
docker run --rm --gpus all `
  --mount type=bind,source="${PWD}\data\cifar-10",target=/app/data/cifar-10 `
  --mount type=bind,source="${PWD}\outputs",target=/app/outputs `
  task3-image-benchmark
```

Run with explicit arguments (including seed):

```powershell
docker run --rm --gpus all `
  --mount type=bind,source="${PWD}\data\cifar-10",target=/app/data/cifar-10 `
  --mount type=bind,source="${PWD}\outputs",target=/app/outputs `
  task3-image-benchmark `
  python app.py --seed 42 --splits 0.8 --epochs 3 --max-samples 15000 --log-level INFO
```

## Every CLI parameter (Python + Docker)

All parameters are identical for Python and Docker.  
For Docker, pass them after:

```powershell
task3-image-benchmark python app.py ...
```

| Parameter | Default | Purpose | Python example | Docker example |
|---|---|---|---|---|
| `--data-root` | `data/cifar-10` | Dataset root folder. | `python app.py --data-root "data/cifar-10"` | `... python app.py --data-root "/app/data/cifar-10"` |
| `--labels-file` | auto from `data-root` | Path to labels CSV (`id,label`). | `python app.py --labels-file "data/cifar-10/trainLabels.csv"` | `... python app.py --labels-file "/app/data/cifar-10/trainLabels.csv"` |
| `--train-dir` | auto from `data-root` | Folder with training PNG files. | `python app.py --train-dir "data/cifar-10/train/train"` | `... python app.py --train-dir "/app/data/cifar-10/train/train"` |
| `--test-dir` | auto from `data-root` | Folder with test PNG files. | `python app.py --test-dir "data/cifar-10/test/test"` | `... python app.py --test-dir "/app/data/cifar-10/test/test"` |
| `--submission-template` | auto from `data-root` | CSV template (usually `sampleSubmission.csv`). | `python app.py --submission-template "data/cifar-10/sampleSubmission.csv"` | `... python app.py --submission-template "/app/data/cifar-10/sampleSubmission.csv"` |
| `--submission-file` | `submission_best.csv` | Output filename for predictions. | `python app.py --submission-file "submission_seed42.csv"` | `... python app.py --submission-file "submission_seed42.csv"` |
| `--skip-submission` | `False` | Skip final submission model training + CSV generation. | `python app.py --skip-submission` | `... python app.py --skip-submission` |
| `--max-test-images` | all images | Limit test images (debug only). | `python app.py --max-test-images 1000` | `... python app.py --max-test-images 1000` |
| `--models` | `mobilenetv2,efficientnetb0,resnet50` | Comma-separated model list. | `python app.py --models "mobilenetv2,resnet50"` | `... python app.py --models "mobilenetv2,resnet50"` |
| `--splits` | `0.7,0.8,0.85` | Comma-separated train ratios. | `python app.py --splits "0.8,0.85"` | `... python app.py --splits "0.8,0.85"` |
| `--epochs` | `4` | Max training epochs. | `python app.py --epochs 6` | `... python app.py --epochs 6` |
| `--batch-size` | `64` | Batch size for train/val/test datasets. | `python app.py --batch-size 32` | `... python app.py --batch-size 32` |
| `--image-size` | `160` | Input resize for model backbone. | `python app.py --image-size 192` | `... python app.py --image-size 192` |
| `--learning-rate` | `0.001` | Adam learning rate. | `python app.py --learning-rate 0.0005` | `... python app.py --learning-rate 0.0005` |
| `--patience` | `2` | EarlyStopping patience (`val_accuracy`). | `python app.py --patience 3` | `... python app.py --patience 3` |
| `--weights` | `imagenet` | Backbone weights: `imagenet` or `none`. | `python app.py --weights none` | `... python app.py --weights none` |
| `--val-ratio` | `0.1` | Validation ratio from training split. | `python app.py --val-ratio 0.15` | `... python app.py --val-ratio 0.15` |
| `--max-samples` | all samples | Limit labeled training rows (debug/speed). | `python app.py --max-samples 12000` | `... python app.py --max-samples 12000` |
| `--preview-samples` | `16` | Number of images in prediction preview plot. | `python app.py --preview-samples 24` | `... python app.py --preview-samples 24` |
| `--output-dir` | `outputs` | Output folder for metrics, plots, submission. | `python app.py --output-dir "outputs_seed42"` | `... python app.py --output-dir "outputs_seed42"` |
| `--save-models` | `False` | Save each evaluated full model (`.keras`) in addition to always-saved weights. | `python app.py --save-models` | `... python app.py --save-models` |
| `--evaluate-model-path` | disabled | Validation-only mode: path to trained `.weights.h5` or `.keras`. | `python app.py --evaluate-model-path "outputs\models\resnet50_train90_test10.weights.h5"` | `... python app.py --evaluate-model-path "/app/outputs/models/resnet50_train90_test10.weights.h5"` |
| `--evaluate-model-name` | inferred/none | Model name for validation mode (needed when filename has no model tag). | `python app.py --evaluate-model-name resnet50` | `... python app.py --evaluate-model-name resnet50` |
| `--evaluate-split` | inferred/none | Train split ratio used in the original run (needed when filename has no split tag). | `python app.py --evaluate-split 0.9` | `... python app.py --evaluate-split 0.9` |
| `--seed` | `42` | Global reproducibility seed. | `python app.py --seed 42` | `... python app.py --seed 42` |
| `--log-level` | `INFO` | Logging level (`DEBUG/INFO/WARNING/ERROR/CRITICAL`). | `python app.py --log-level DEBUG` | `... python app.py --log-level DEBUG` |

## Output files

All outputs are written to `Task3\outputs\` (or custom `--output-dir`):

- `summary.csv`, `summary.json` - all experiment rows,
- `best_models_by_split.csv` - best model per split,
- `best_overall.json` - best model overall,
- `validation_check_<model>_trainXX_testYY.json` - validation-only metrics for a loaded trained model,
- `submission_best.csv` (or custom name) - predicted test labels,
- `plots\` - ROC curves, confusion matrices, prediction previews, and validation-check plots,
- `models\` - saved model weights for every run (`<model>_trainXX_testYY.weights.h5`) and optional full models (`.keras`) when `--save-models` is used.

## Dataset source

https://www.kaggle.com/competitions/cifar-10/data
