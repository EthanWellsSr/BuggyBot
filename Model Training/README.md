# Model Training

Training code for the traffic-sign classifier (Self-Driving RC Car).

Current status: `train_gtsrb.py` trains and saves the GTSRB model. It uses a
physical-sign-track split so neighboring frames of the same sign cannot appear in
both training and validation. `evaluate_gtsrb.py` independently tests the saved
model and writes the results to `gtsrb_test_results.json`.

Latest verified fresh-training result:

- Track-separated validation: **97.09% top-1**.
- Independent GTSRB test set: **95.79% top-1**, **98.45% top-3**.
- Test macro class accuracy: **93.83%**.
- Test predictions: **12,098 correct / 532 incorrect** across 12,630 images.

The LISA source dataset contains 47 US traffic-sign classes. The current
model-specific dataset retains 12 selected classes. Download and preparation
instructions are in [`LISA_PREPARATION.md`](LISA_PREPARATION.md). The preparation
script is `prepare_lisa.py`; model training and testing are intentionally separate.

## Setup

Requires **Python 3.12** (TensorFlow has no wheels for 3.13/3.14 yet). From this
folder:

```
python3.12 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install tensorflow
```

## Train

```
python train_gtsrb.py
```

Loads `GTSRB/Train.csv`, creates a class-stratified 80/20 split by physical sign
track, trains for up to 40 epochs, and saves the best model to
`gtsrb_model.keras`. Early stopping may finish sooner.

The model uses 32×32 RGB input, realistic geometric and lighting augmentation,
class balancing, two convolutional blocks, batch normalization, dropout, global
average pooling, and a 43-class softmax output. Training stops when validation
loss stops improving, restores the best weights, and saves only
`gtsrb_model.keras`.

## Test

```
python evaluate_gtsrb.py
```

This evaluates the saved model on all 12,630 labeled images in `GTSRB/Test.csv`
and writes top-1, top-3, macro class accuracy, per-class accuracy, and common
confusions to `gtsrb_test_results.json`. Use the track-separated validation set
for model selection; reserve this independent test set for final evaluation.


## Dataset: GTSRB (German Traffic Sign Recognition Benchmark)

The dataset is **not** committed to the repo (too large; publicly re-downloadable).
To set it up:

1. Make a free Kaggle account.
2. Download the ZIP from
   https://www.kaggle.com/datasets/meowmeowmeowmeowmeow/gtsrb-german-traffic-sign?resource=download
   (the "Download" button).
3. Unzip it into `Model Training/GTSRB/` so the layout is:

   ```
   Model Training/GTSRB/
       Train/       43 class folders (0-42), images inside  <- used for training
       Test/        12,630 flat images; labels in Test.csv  <- final testing later
       Meta/        one reference image per sign class
       Train.csv  Test.csv  Meta.csv
   ```

`GTSRB/` is gitignored.
