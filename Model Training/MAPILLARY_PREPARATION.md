# Preparing Mapillary signs for the LISA classes

This creates a **separate, reviewable Mapillary dataset** with the same 12 class names and file layout as `LISA/prepared`. It does not change LISA images or train a model.

## Inputs

Download the **v2 fully annotated** Mapillary Traffic Sign Dataset from [Mapillary](https://www.mapillary.com/dataset/trafficsign) after accepting its terms yourself. Place these five files in `Model Training/LISA/mapillary_raw/`:

```text
mtsd_v2_fully_annotated_annotation.zip
mtsd_v2_fully_annotated_images.train.0.zip
mtsd_v2_fully_annotated_images.train.1.zip
mtsd_v2_fully_annotated_images.train.2.zip
mtsd_v2_fully_annotated_images.val.zip
```

The ZIPs remain intact. The script reads only matched source images and writes the sign crops as regular PNG files. Mapillary's test image ZIP is unnecessary because the released test images have no annotation JSON in the fully annotated package. The five files above were checked against Mapillary's published MD5 values for this run; the script also checks that image keys exactly cover the published train/validation split.

| Archive | Expected MD5 |
| --- | --- |
| annotations | `99394f7890112823880d14525c54467a` |
| train.0 | `982ea17dcb412f7fe57fa15a8cf91175` |
| train.1 | `008028e616f4bdd26cfcf802715f29eb` |
| train.2 | `48fd11f9bc1048b9ffa54a95605976b5` |
| val | `f1be4cb09ffcbd7c2850f7ac2ed2760f` |

`LISA/` is Git ignored. Keep the raw ZIPs, prepared images, galleries, and exclusions out of Git. Follow the [Mapillary dataset terms](https://www.mapillary.com/dataset/trafficsign) when sharing data with classmates.

## Prepare

From `Model Training/`, use the existing TensorFlow environment:

```bash
./.venv/bin/python prepare_mapillary.py
```

The default output is `LISA/mapillary_prepared/`. The script refuses to overwrite an existing output. To produce a reviewed revision, edit `LISA/mapillary_raw/exclusions.csv` and choose a new output:

```bash
./.venv/bin/python prepare_mapillary.py --output LISA/mapillary_prepared_v2
```

The command also accepts `--source`, `--exclusions`, and `--seed` for other installations or repeatable split choices. It needs TensorFlow and the Python standard library; it does not require extracting the ZIPs.

## Selection and split

- Twelve explicit Mapillary sign variants map to the existing LISA labels. The mapping is recorded in `summary.json` and can be edited near the top of `prepare_mapillary.py` after visual review.
- A source sign box must be at least 24 pixels on both sides. The script excludes ambiguous, dummy, cut-off, nested, and panorama annotations. Occluded signs remain, with a flag in the manifest.
- Each box becomes a square PNG crop with at least a 32-pixel side, using surrounding context rather than stretching the sign.
- Mapillary's published validation images become this dataset's held-out **test** split. Its published training images are assigned to **train** or **validation** by a seeded image-key hash. All signs from one source image stay in one split. The script ensures at least two validation crops per class when possible.
- Mapillary does not provide LISA-style physical sign tracks. Similar views of one physical sign could still cross splits. Treat results accordingly and inspect the source IDs before claiming independent-sign accuracy.

## Output and review

```text
LISA/mapillary_prepared/
  train/<class_directory>/*.png
  validation/<class_directory>/*.png
  test/<class_directory>/*.png
  classes.csv
  manifest.csv
  summary.json
  review/index.html
```

Open `review/index.html` locally to inspect the crops class by class. Each caption gives `image_key,object_key`. To omit a crop in the next preparation run, add a line to `LISA/mapillary_raw/exclusions.csv`:

```csv
image_key,object_key,reason
example_image_key,example_object_key,not_US_style
```

Keep the header and replace the example with real IDs from the gallery. The script stops if an exclusion does not match a mapped annotation, so typos cannot silently pass. Check all classes before using the images for training. In particular, Mapillary's general `stop` label includes non-English words such as **PARE**, and a speed-limit sample was a truck-specific sign. Those are in the initial gallery for review, not automatically treated as equivalent to ordinary US signs.

`classes.csv` uses the same class order as the current LISA dataset. `manifest.csv` records the original ZIP, source image, object ID, bounding box, flags, and split for every crop. `summary.json` records selection counts and split limits. `train_lisa.py` remains pointed at `LISA/prepared`; the separate `train_mapillary.py` reads `LISA/mapillary_prepared` and writes its own model and diagnostic report.
