# Preparing the LISA Traffic-Sign Dataset

This step creates a classification dataset. It does not train or test a model.

## 1. Get the original dataset

Use the official [UCSD LISA Traffic Signs Dataset page](https://cvrr.ucsd.edu/lisa-traffic-signs-dataset).
The dataset is distributed under an academic license, so read and accept its terms before downloading it.
The page links to the original UCSD NAS download host.

The NAS host was not responding when these instructions were written on September 28, 2026. If it is still down,
use the third-party [Kaggle mirror](https://www.kaggle.com/datasets/omkarnadkarni/lisa-traffic-sign).
That mirror is about 9.65 GB and requires a Kaggle account. It is not the authoritative license source, so the
original LISA academic license still governs use of the data.

Do not download the **LISA Traffic Light Dataset** by mistake. It is a different dataset.

The correct archive contains `allAnnotations.csv`, `categories.txt`, and directories with names such as
`aiua120214-0`. The expected dataset has 47 traffic-sign labels and 7,855 annotations.

## 2. Unpack it locally

Create this local layout:

```text
Model Training/
  LISA/
    raw/
      allAnnotations.csv
      categories.txt
      aiua120214-0/
      ...
```

`LISA/` is ignored by Git because the original and generated images must not be committed.

## 3. Run the preparation script

From `Model Training/`, with the existing virtual environment active:

```bash
python prepare_lisa.py --source LISA/raw --output LISA/prepared
```

The script deliberately refuses to use an existing output directory. This prevents an accidental mixture of two
runs. Rename or remove an old generated directory before rerunning.

**The script modifies `LISA/raw/` in place.** After validation it deletes everything the classifier does not need
(about 4 GB): `negatives/`, `tools/`, `readme.txt`, `datasetDescription.pdf`, `videoSources.txt`, and the per-folder
`frameAnnotations.csv`/`.bak`/`Thumbs.db` copies. What remains is `allAnnotations.csv`, `categories.txt`, and the
6,618 annotated frames (about 5 GB). Pass `--no-strip` to keep the original download untouched.

## What the script does

1. Reads the semicolon-delimited `allAnnotations.csv` file.
2. Requires exactly 47 labels, preventing the wrong LISA dataset or an incomplete archive from passing unnoticed.
3. Confirms every annotated frame exists on disk.
4. Strips unneeded files from the source dataset (skipped with `--no-strip`). Nothing is deleted unless steps 2
   and 3 pass.
5. Uses each annotation's bounding box to crop one traffic sign.
6. Expands each crop to a square without stretching the sign. Very small boxes receive surrounding image context
   until the crop reaches at least 32×32 pixels.
7. Assigns repeated frames from the same annotated sign track to one split. This prevents nearly identical views of
   one physical sign from appearing in both training and evaluation data.
8. Creates an approximately 80/10/10 train/validation/test split independently for each class. Classes with too few
   independent tracks may be absent from validation or test; those cases are reported instead of hidden.

The output is compatible with TensorFlow's `image_dataset_from_directory`:

```text
LISA/prepared/
  train/<class_directory>/*.png
  validation/<class_directory>/*.png
  test/<class_directory>/*.png
  classes.csv
  manifest.csv
  summary.json
```

- `classes.csv` maps TensorFlow's numeric class index to the original LISA label and gives per-split counts.
- `manifest.csv` traces every crop to its source image, original bounding box, split, and track.
- `summary.json` records totals and identifies classes missing from validation or test.

## Completion check

Before any model-specific class filtering, preparation is complete only when:

- the command exits successfully;
- `summary.json` reports 47 classes and 7,855 annotations;
- every output image is represented in `manifest.csv`;
- any missing validation/test coverage in `summary.json` has been reviewed.

Training and evaluation of a new LISA model are separate next-week tasks.
