# Combined LISA and Mapillary dataset

The combined classifier uses the same 12 class indices as the separate LISA and
Mapillary models. Prepare both sources first, following
[`LISA_PREPARATION.md`](LISA_PREPARATION.md) and
[`MAPILLARY_PREPARATION.md`](MAPILLARY_PREPARATION.md). From `Model Training/`, run:

```sh
python3 prepare_combined.py
```

This creates `LISA/Combined/`, with `train/`, `validation/`, and `test/` class
folders, `classes.csv`, `manifest.csv`, and `summary.json`. The PNG files are
copied into the combined class folders with `lisa__` or `mapillary__` filename
prefixes. The manifest retains the original crop path, source dataset, source
image, and group ID. The summary includes SHA-256 hashes of both input
manifests and class tables so a run can be tied to the prepared inputs.

| Source | Train | Validation | Test | Total |
| --- | ---: | ---: | ---: | ---: |
| LISA | 4,946 | 567 | 584 | 6,097 |
| Mapillary | 2,655 | 362 | 432 | 3,449 |
| Combined | 7,601 | 929 | 1,016 | 9,546 |

The script preserves each source's split. It checks for byte-identical PNGs
across splits and stops if it finds any. LISA uses physical sign tracks for its
split. Mapillary uses source image IDs; its images cannot be confirmed to have
distinct physical signs across splits. Physical sign overlap between the two
datasets is also unknown. The combined test set is useful for comparing models
on the same images, but it is not a substitute for a new camera-based test set.

`LISA/` is Git ignored, including `Combined/`. To rebuild after changing either
source, move or remove `LISA/Combined/`, then rerun the preparation script.
The script will not overwrite an existing combined dataset.

Train after preparation:

```sh
./.venv/bin/python train_combined.py
```

Training saves `combined_model.keras` and `combined_training_report.json` in
`Model Training/`. The report includes epoch history, overall validation and
test results, results by source dataset, per-class metrics, confusion matrices,
and individual errors. The trainer uses the same architecture and training
settings as the separate LISA and Mapillary trainers. Training can take longer
because it uses all 7,601 training crops.

After training, run `./.venv/bin/python evaluate_combined_models.py` to score
the LISA, Mapillary, and combined models on the same 1,016 test crops. The
script writes `combined_model_comparison_report.json` and
`combined_model_comparison.md`.
