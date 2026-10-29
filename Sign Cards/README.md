# BuggyBot sign cards

Twelve printable signs, one for each class used by the LISA, Mapillary, and
combined classifiers. The front of each card contains only the sign artwork.
The filenames identify the classes without putting labels in the camera view.

- [`print_all_12_letter.pdf`](print_all_12_letter.pdf): three US Letter pages,
  four 3 x 5 inch cards per page, with light gray cut lines.
- `cards/`: one 3 x 5 inch PDF per sign class for printing on index cards.
- `artwork/`: the downloaded 960-pixel PNGs used to build the PDFs. The crop
  script also uses them as matching templates.
- `Test Images/`: BuggyBot camera photos of these cards; see below.

Print at **100% / actual size** on white matte card stock. Disable "fit to
page" or scaling. Cut on the light gray lines in the letter-size PDF. Avoid
glossy reflections during camera testing. The live sign demo in
[`Model Training/OpenCV/`](../Model%20Training/OpenCV/README.md) detects these
cards on the car's camera.

## Camera test photos

`Test Images/` holds an independent test of the classifiers on printed cards
photographed by BuggyBot's Camera Module 3. It covers 10 of the 12 classes;
speed limits 30 and 35 were left out because the track will not use them.

```text
Test Images/
  raw/<class>/<condition>/<class>_NNN.jpg       full-resolution photos (Git ignored)
  cropped/<class>/<condition>/<class>_NNN.png   sign crops (committed)
  cropped/manifest.csv                          source photo, crop box, match score
  cropped/review.html                           crop gallery, lowest score first
```

Folder names must be the exact class names from `artwork/` (for example
`speedLimit25`, `pedestrianCrossing`). The three conditions are `no_light`,
`sunlight`, and `sunlight_and_artificial`. The October 2026 set has 329 photos:
11 per class and condition (10 for `stop/no_light`).

The 11 photos in each folder were taken 2 seconds apart without moving the
card, so they are near-duplicates. The set contains about 30 distinct setups
(class × condition), not 329 independent views. Report it that way.

**Taking photos.** On BuggyBot, one folder at a time:

```bash
rpicam-still -n -t 30000 --timelapse 2000 --autofocus-on-capture -o stop_%03d.jpg
```

Copy them to your computer with `scp` into `raw/<class>/<condition>/`. The raw
photos are about 0.8 MB each, so they stay out of Git; only the crops are
committed.

**Cropping.** Run `Model Training/scripts/crop_sign_photos.py`. It finds each
card by OpenCV template matching against its class artwork, uses the fact that
the card stays in the same place within a folder, and writes tight square
crops (the same style as the training data) to `cropped/`. Check
`review.html`; a low score usually means a wrong folder name or a missed sign.
Because the script knows each photo's class, these crops are better placed
than a detector on the car would produce.

**Testing.** Run `Model Training/scripts/evaluate_sign_photos.py`; results are
in [`sign_photo_test_results.md`](../Model%20Training/reports/sign_photo_test_results.md).
The combined model classified all 329 crops correctly. If the car later
misreads signs, compare its crops with these before suspecting the model.

## Artwork sources

The signs are MUTCD-style U.S. traffic-control designs. The warning and
regulatory artwork comes from public-domain MUTCD designs hosted on Wikimedia
Commons. The five speed-limit files were dedicated to the public domain by
their creator. Source and reuse information is on each linked file page.

| Model class | Sign | Source file |
| --- | --- | --- |
| `addedLane` | W4-3R Added Lane | [MUTCD W4-3R.svg](https://commons.wikimedia.org/wiki/File:MUTCD_W4-3R.svg) |
| `keepRight` | R4-7 Keep Right | [MUTCD R4-7.svg](https://commons.wikimedia.org/wiki/File:MUTCD_R4-7.svg) |
| `merge` | W4-1R Merge | [MUTCD W4-1R.svg](https://commons.wikimedia.org/wiki/File:MUTCD_W4-1R.svg) |
| `pedestrianCrossing` | W11-2 Pedestrian | [MUTCD W11-2.svg](https://commons.wikimedia.org/wiki/File:MUTCD_W11-2.svg) |
| `school` | S1-1 School | [MUTCD S1-1.svg](https://commons.wikimedia.org/wiki/File:MUTCD_S1-1.svg) |
| `signalAhead` | W3-3 Signal Ahead | [MUTCD W3-3.svg](https://commons.wikimedia.org/wiki/File:MUTCD_W3-3.svg) |
| `speedLimit25` | R2-1 Speed Limit 25 | [Speed Limit 25 sign.svg](https://commons.wikimedia.org/wiki/File:Speed_Limit_25_sign.svg) |
| `speedLimit30` | R2-1 Speed Limit 30 | [Speed Limit 30 sign.svg](https://commons.wikimedia.org/wiki/File:Speed_Limit_30_sign.svg) |
| `speedLimit35` | R2-1 Speed Limit 35 | [Speed Limit 35 sign.svg](https://commons.wikimedia.org/wiki/File:Speed_Limit_35_sign.svg) |
| `speedLimit45` | R2-1 Speed Limit 45 | [Speed Limit 45 sign.svg](https://commons.wikimedia.org/wiki/File:Speed_Limit_45_sign.svg) |
| `speedLimit65` | R2-1 Speed Limit 65 | [Speed Limit 65 sign.svg](https://commons.wikimedia.org/wiki/File:Speed_Limit_65_sign.svg) |
| `stop` | R1-1 Stop | [MUTCD R1-1.svg](https://commons.wikimedia.org/wiki/File:MUTCD_R1-1.svg) |

These cards are for controlled model evaluation, not for road use. They test
printed-sign recognition under chosen lighting, distance, and angle. Road-scene
accuracy in the training reports does not predict this physical test result.
