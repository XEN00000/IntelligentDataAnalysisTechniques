
# Polecenie do szybkiej klasyfikacji (mały zbiór)

## Lokalne (Python):
```powershell
python app.py --seed 42 --max-samples 100 --models mobilenetv2 --splits 0.8 --epochs 1 --skip-submission --log-level INFO
```

## Docker:
```powershell
docker run --rm --gpus all `
  --mount type=bind,source="${PWD}\data\cifar-10",target=/app/data/cifar-10 `
  --mount type=bind,source="${PWD}\outputs",target=/app/outputs `
  task3-image-benchmark `
  python app.py --seed 42 --max-samples 100 --models mobilenetv2 --splits 0.8 --epochs 1 --skip-submission --log-level INFO
```

> [!NOTE]
> `--max-samples 100` załaduje tylko 100 obrazków treningowych (stratyfikowany sampling, po 10 z klasy).
> Z podziałem 80/20 da to 80 treningowych + 20 testowych — wystarczające do sprawdzenia że pipeline działa.
> Przy `--epochs 1` cały run powinien trwać <30 sekund.

## Wariant "10 zdjęć do testowania":
```powershell
python app.py --seed 42 --max-samples 100 --models mobilenetv2 --splits 0.9 --epochs 1 --skip-submission --log-level INFO
```
To da 90 treningowych i 10 testowych — potwierdza że klasyfikacja działa na minimalnym zbiorze.

> [!WARNING]
> Przy <100 próbkach wyniki będą losowe — to jest wyłącznie do testu że pipeline się nie wywala, NIE do oceny jakości.
