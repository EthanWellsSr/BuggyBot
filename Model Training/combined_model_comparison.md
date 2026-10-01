# Three-model comparison on the combined test set

All three saved models were evaluated on the same 1,016 held-out crops
(584 LISA and 432 Mapillary). Per-sign accuracy below means recall:
correct predictions divided by test examples of that sign.

| Model | Correct / 1,016 | Top-1 | Top-3 | Macro F1 | LISA top-1 | Mapillary top-1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| lisa | 863 / 1016 | 84.94% | 97.15% | 76.03% | 89.90% | 78.24% |
| mapillary | 732 / 1016 | 72.05% | 90.35% | 54.71% | 56.85% | 92.59% |
| combined | 1009 / 1016 | 99.31% | 99.80% | 98.55% | 99.66% | 98.84% |

## Accuracy by sign

| Sign | Test crops | LISA model | Mapillary model | Combined model |
| --- | ---: | ---: | ---: | ---: |
| addedLane | 31 | 87.10% | 16.13% | 100.00% |
| keepRight | 60 | 93.33% | 100.00% | 100.00% |
| merge | 45 | 35.56% | 46.67% | 95.56% |
| pedestrianCrossing | 202 | 84.16% | 82.18% | 100.00% |
| school | 36 | 36.11% | 58.33% | 94.44% |
| signalAhead | 176 | 92.61% | 53.98% | 100.00% |
| speedLimit25 | 60 | 91.67% | 91.67% | 100.00% |
| speedLimit30 | 33 | 57.58% | 87.88% | 100.00% |
| speedLimit35 | 33 | 69.70% | 48.48% | 100.00% |
| speedLimit45 | 34 | 70.59% | 14.71% | 100.00% |
| speedLimit65 | 16 | 87.50% | 0.00% | 87.50% |
| stop | 290 | 97.59% | 89.31% | 99.66% |

The [JSON report](combined_model_comparison_report.json) also contains
per-source per-class metrics, confusion matrices, individual errors,
and paired differences on identical images.

The combined test set preserves each source's original split. Exact PNG
duplicates across splits were checked during preparation. Physical sign
overlap across Mapillary images or between datasets remains unknown.
These results measure cropped road-scene signs, not the camera and
detection pipeline on BuggyBot.
