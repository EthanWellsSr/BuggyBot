# Model Training

Training code for the traffic-sign classifier (Self-Driving RC Car).

There are separate classifiers for German (GTSRB) and US (LISA) signs. The
dataset preparation keeps neighboring frames of the same physical sign in one
split, so validation and test images come from different sign tracks than the
training images.

## LISA: US signs

The source dataset has 47 classes. This project's current classifier uses 12
selected classes: added lane, keep right, merge, pedestrian crossing, school,
signal ahead, speed limits 25/30/35/45/65, and stop. The prepared subset has
4,946 training, 567 validation, and 584 test crops. See
[`LISA_PREPARATION.md`](LISA_PREPARATION.md) for download and preparation.

From this folder, run `python train_lisa.py`. It trains the classifier, restores
the weights from the epoch with the lowest validation loss, saves
`lisa_model.keras`, and evaluates that model on both validation and held-out test
crops. It writes one `lisa_training_report.json` with training settings, class
weights, crop and sign-track counts, every epoch's loss/accuracy/learning rate,
per-class precision/recall/F1, full confusion matrices, and every mistaken
crop's source track and prediction probabilities. Use validation results to
choose training changes; treat test results as the final check.

The first trained model and its report are archived as `lisa_model_v1.keras`
and `lisa_test_results_v1.json` for comparison with later runs. That model
scored **89.90% top-1**, **99.14% top-3**, and **84.93% macro class accuracy**
on the 584 test crops (525 correct, 59 incorrect). Those results cover LISA
road-scene crops, not printed signs viewed by the car's camera.

## Mapillary: separate US-sign candidate set

The fully annotated Mapillary archives are stored locally under
`LISA/mapillary_raw/`. Run `prepare_mapillary.py` to create a separate
12-class crop dataset under `LISA/mapillary_prepared/` and open its
`review/index.html` to inspect the images. The class names and metadata layout
match LISA, but Mapillary's source split and sign-identity information differ.
See [`MAPILLARY_PREPARATION.md`](MAPILLARY_PREPARATION.md) for the exact inputs,
filtering, split method, review workflow, and limitations. These images have
not been merged with LISA or used to train a model.

## GTSRB: German signs

Run `python train_gtsrb.py` to train and save `gtsrb_model.keras`. The script
creates a class-stratified 80/20 split by physical sign track from
`GTSRB/Train.csv`, trains for up to 40 epochs, and restores the best validation
weights. Run `python evaluate_gtsrb.py` to test that model on the 12,630 images
in `GTSRB/Test.csv` and write `gtsrb_test_results.json`.

Latest verified GTSRB result:

- Track-separated validation: **97.09% top-1**.
- Independent GTSRB test set: **95.79% top-1**, **98.45% top-3**.
- Test macro class accuracy: **93.83%**.
- Test predictions: **12,098 correct / 532 incorrect** across 12,630 images.

## Setup

Use **Python 3.12** in this folder's virtual environment. Install packages
through that environment so the system Python's packages do not interfere:

```
python3.12 -m venv .venv
./.venv/bin/python -m pip install tensorflow
./.venv/bin/python train_lisa.py
```

If `.venv` already has TensorFlow, run only the final command. On Windows, use
`.venv\Scripts\python.exe` in place of `./.venv/bin/python`.

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
