# BuggyBot sign cards

Twelve printable signs, one for each class used by the LISA, Mapillary, and
combined classifiers. The front of each card contains only the sign artwork.
The filenames identify the classes without putting labels in the camera view.

- [`print_all_12_letter.pdf`](print_all_12_letter.pdf): three US Letter pages,
  four 3 x 5 inch cards per page, with light gray cut lines.
- `cards/`: one 3 x 5 inch PDF per sign class for printing on index cards.
- `artwork/`: the downloaded 960-pixel PNGs used to build the PDFs.

Print at **100% / actual size** on white matte card stock. Disable "fit to
page" or scaling. Cut on the light gray lines in the letter-size PDF. Avoid
glossy reflections during camera testing. These are classification test cards;
the repository's camera pipeline does not yet locate signs automatically.

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
