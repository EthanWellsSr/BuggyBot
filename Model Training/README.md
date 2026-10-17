# Model Training

Training code for BuggyBot's traffic-sign classifiers.

GTSRB supplies German signs. LISA and Mapillary supply separate experiments
using the same 12 selected US-sign class names and numeric indices. LISA's
dataset preparation keeps neighboring frames of the same physical sign in one
split. Mapillary provides image IDs but not physical sign track IDs; its splits
keep source images separate without proving physical-sign independence.

## Layout

```text
Model Training/
  scripts/     prepare_*, train_*, evaluate_* scripts
  models/      saved .keras models
  reports/     training, test, and comparison reports
  docs/        dataset preparation guides
  data/        Git-ignored datasets
    raw/         gtsrb/, lisa/, mapillary/ (downloads and review files)
    prepared/    lisa/, mapillary/, combined/ (generated crop datasets)
  requirements.txt
```

Scripts locate everything relative to `Model Training/`, so they run from the
IDE regardless of working directory.

## Setup

Use **Python 3.12** with this folder's `.venv` as the IDE interpreter, and
install `requirements.txt` into it. The pinned versions match the environment
that produced the saved models and reports.

## LISA: US signs

The source dataset has 47 classes. This project's current classifier uses 12
selected classes: added lane, keep right, merge, pedestrian crossing, school,
signal ahead, speed limits 25/30/35/45/65, and stop. The prepared subset has
4,946 training, 567 validation, and 584 test crops. See
[`docs/LISA_PREPARATION.md`](docs/LISA_PREPARATION.md) for download and
preparation.

Run `scripts/train_lisa.py`. It trains the classifier, restores the weights
from the epoch with the lowest validation loss, saves `models/lisa_model.keras`,
and evaluates that model on both validation and held-out test crops. It writes
`reports/lisa_training_report.json` with training settings, class weights, crop
and sign-track counts, every epoch's loss/accuracy/learning rate, per-class
precision/recall/F1, full confusion matrices, and every mistaken crop's source
track and prediction probabilities. Use validation results to choose training
changes; treat test results as the final check.

The saved LISA model scored **89.90% top-1**, **99.14% top-3**, and **84.93%
macro class accuracy** on the 584 test crops (525 correct, 59 incorrect). Those
results cover LISA road-scene crops, not printed signs viewed by the car's
camera.

## Mapillary: separate US-sign candidate set

`scripts/prepare_mapillary.py` builds a separate 12-class crop dataset under
`data/prepared/mapillary/`; open its `review/index.html` to inspect the images.
It contains 2,655 train, 362 validation, and 432 test crops. See
[`docs/MAPILLARY_PREPARATION.md`](docs/MAPILLARY_PREPARATION.md) for the
inputs, filtering, split method, review workflow, and limitations. The source
ZIPs have been removed locally; re-download them before re-preparing.

Run `scripts/train_mapillary.py` to train a model with the same architecture
and settings as the LISA run. It saves `models/mapillary_model.keras` and
`reports/mapillary_training_report.json`, including epoch history, per-class
metrics, confusion matrices, and individual errors. The first local Mapillary
run completed 49 epochs and scored **92.59% top-1** (400/432), **98.84%
top-3**, and **77.98% macro F1** on its test crops. Speed-limit-65 had only two
test examples and neither was classified correctly.

## Combined: LISA and Mapillary US signs

Run `scripts/prepare_combined.py` after preparing both source datasets. It
creates `data/prepared/combined/` with 7,601 train, 929 validation, and 1,016
test crops. The 12 class indices and each source image's existing split are
preserved. See [`docs/COMBINED_PREPARATION.md`](docs/COMBINED_PREPARATION.md)
for the layout, reproducible steps, and split limitations.

Run `scripts/train_combined.py` to train with the same architecture and
settings as the separate models. It saves `models/combined_model.keras` and
`reports/combined_training_report.json`. The report includes results on the
combined validation and test sets and a breakdown for LISA and Mapillary
images. The first combined run completed 51 epochs and scored **99.31% top-1**
(1,009/1,016) and **98.55% macro F1** on its test crops.

To compare all three saved models on exactly the same held-out images, run
`scripts/evaluate_combined_models.py`. It loads the LISA, Mapillary, and
combined models, checks that their class labels and original test scores match
the training reports, then writes `reports/combined_model_comparison_report.json`
and a readable `reports/combined_model_comparison.md`. These give overall and
per-source accuracy, per-class recall, macro F1, confusion matrices, and
individual errors. The comparison uses only `data/prepared/combined/test`
(1,016 crops), not training images.

## GTSRB: German signs

See [`docs/GTSRB_PREPARATION.md`](docs/GTSRB_PREPARATION.md) for download and
layout. Run `scripts/train_gtsrb.py` to train and save
`models/gtsrb_model.keras`. The script creates a class-stratified 80/20 split by
physical sign track from `Train.csv`, trains for up to 40 epochs, and restores
the best validation weights. Run `scripts/evaluate_gtsrb.py` to test that model
on the 12,630 images in `Test.csv` and write `reports/gtsrb_test_results.json`.

Latest verified GTSRB result:

- Track-separated validation: **97.09% top-1**.
- Independent GTSRB test set: **95.79% top-1**, **98.45% top-3**.
- Test macro class accuracy: **93.83%**.
- Test predictions: **12,098 correct / 532 incorrect** across 12,630 images.
