# Sign-card photo test

329 BuggyBot camera photos of the printed sign cards, cropped by
`scripts/crop_sign_photos.py`, shuffled (seed 123), and classified by each US-sign model.
Only the classes photographed so far are included.

| Model | Top-1 | Top-3 |
| --- | ---: | ---: |
| lisa | 47.7% (157/329) | 99.1% |
| mapillary | 79.9% (263/329) | 96.7% |
| combined | 100.0% (329/329) | 100.0% |

## Accuracy by sign

| Sign | Photos | lisa | mapillary | combined |
| --- | ---: | ---: | ---: | ---: |
| addedLane | 33 | 33.3% | 100.0% | 100.0% |
| keepRight | 33 | 72.7% | 100.0% | 100.0% |
| merge | 33 | 0.0% | 100.0% | 100.0% |
| pedestrianCrossing | 33 | 100.0% | 100.0% | 100.0% |
| school | 33 | 0.0% | 100.0% | 100.0% |
| signalAhead | 33 | 51.5% | 100.0% | 100.0% |
| speedLimit25 | 33 | 100.0% | 100.0% | 100.0% |
| speedLimit45 | 33 | 21.2% | 0.0% | 100.0% |
| speedLimit65 | 33 | 0.0% | 0.0% | 100.0% |
| stop | 32 | 100.0% | 100.0% | 100.0% |

## Accuracy by lighting

| Condition | Photos | lisa | mapillary | combined |
| --- | ---: | ---: | ---: | ---: |
| no_light | 109 | 31.2% | 79.8% | 100.0% |
| sunlight | 110 | 57.3% | 80.0% | 100.0% |
| sunlight_and_artificial | 110 | 54.5% | 80.0% | 100.0% |

## Most common mistakes

- **lisa:** merge → pedestrianCrossing (33), school → pedestrianCrossing (33), speedLimit65 → speedLimit25 (32), addedLane → pedestrianCrossing (22), signalAhead → pedestrianCrossing (16)
- **mapillary:** speedLimit65 → speedLimit25 (33), speedLimit45 → speedLimit30 (29), speedLimit45 → speedLimit25 (4)
- **combined:** none
