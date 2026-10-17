# Preparing the GTSRB Dataset

GTSRB (German Traffic Sign Recognition Benchmark) needs no preparation script.
The training and evaluation scripts read the download directly.

## 1. Get the dataset

1. Make a free Kaggle account.
2. Download the ZIP from the
   [Kaggle GTSRB dataset page](https://www.kaggle.com/datasets/meowmeowmeowmeowmeow/gtsrb-german-traffic-sign?resource=download)
   (the "Download" button).

## 2. Unpack it locally

Unzip it into `Model Training/data/raw/gtsrb/` so the layout is:

```text
Model Training/data/raw/gtsrb/
  Train/       43 class folders (0-42), images inside  <- used for training
  Test/        12,630 flat images; labels in Test.csv  <- final testing
  Meta/        one reference image per sign class
  Train.csv  Test.csv  Meta.csv
```

`data/` is ignored by Git because the dataset is large and publicly
re-downloadable.

## 3. Use it

- `scripts/train_gtsrb.py` reads `Train.csv` and splits it 80/20 by physical
  sign track, so frames of one sign never appear in both training and
  validation.
- `scripts/evaluate_gtsrb.py` reads `Test.csv` and scores the saved model on the
  independent test images.
