# BuggyBot

University of Houston–Clear Lake (UHCL) Senior Project, CENG 4265. The course
deliverables use the project title **Self Driving RC Car**; BuggyBot is the
repository and vehicle name.

BuggyBot is an RC car project intended to follow a controlled course and obey
traffic signs. The fall scope is a stationary sign-recognition system; the
spring scope is the autonomous vehicle.

## Current state

- The bench platform uses a Raspberry Pi Compute Module 5 (CM5) on its IO Board,
  booting Raspberry Pi OS Lite from an M.2 NVMe SSD. USB Wi-Fi supplies network
  access because this CM5 Lite has no onboard wireless.
- [`Hardware/buggybot_integration.py`](Hardware/buggybot_integration.py) captures
  camera images and drives an LCD using **simulated** sign predictions. It does
  not yet run a trained model or control the vehicle from model output.
- TensorFlow classifiers have been trained on GTSRB, LISA, Mapillary, and a
  combined LISA+Mapillary dataset. Their models and results are in this repo.

## Hardware

- **Compute and storage:** Raspberry Pi CM5 (4 GB Lite), CM5 IO Board, M.2 NVMe
- **Networking:** USB Wi-Fi dongle for headless SSH
- **Vision and sensing:** Camera Module 3, HC-SR04 ultrasonic sensor, ICM-20948 IMU
- **Course sensing:** line sensors have been ordered; the exact model and
  Raspberry Pi integration are pending
- **Output and motion:** I²C LCD; motor-control hardware is being developed

The [parts list](Hardware/partslist.md) records purchase and availability
status. Wiring references and hardware test scripts are in [`Hardware/`](Hardware/).

## Traffic-sign models

The image classifiers use 32×32 sign crops. The intended CM5 pipeline will
locate signs in camera frames and run a compact model on-device; that inference
pipeline is not yet implemented in this repository.

| Dataset and model | Classes | Prepared crops | Held-out result | Status |
| --- | ---: | ---: | --- | --- |
| GTSRB, German signs | 43 | See [training guide](Model%20Training/README.md) | 95.79% top-1 on 12,630 test images | Model and evaluation committed |
| LISA, selected US signs | 12 | 6,097 | 89.90% top-1 on 584 test crops | First model archived; training report committed |
| Mapillary, mapped to the same 12 classes | 12 | 3,449 | 92.59% top-1 on 432 test crops | Model and report committed |
| Combined LISA+Mapillary | 12 | 9,546 | 99.31% top-1 on 1,016 combined test crops | Model, training report, and same-set comparison committed |

The separate LISA and Mapillary percentages use **different test sets** and do
not rank those models. The [same-set comparison](Model%20Training/combined_model_comparison.md)
evaluates all three US-sign models on the 1,016 combined test crops. The
combined set preserves each source's split but does not establish physical-sign
independence across datasets. The Mapillary test set has only two speed-limit-65
crops. Camera images captured by BuggyBot are still needed to measure live
performance. See the [model training guide](Model%20Training/README.md) for the
scripts, preparation steps, and detailed results.

## Team

- Ethan Wells (Group Leader)
- Alexis Perez
- Ethan Bishop
- Abigail Duran

**Faculty advisor:** Dr. Nguyen · **TA:** Ruben Ramirez

## Repository layout

| Path | Contents |
| --- | --- |
| `Proposal/` | Project proposal and Gantt charts |
| `Weekly Reports/` | Rolling report and presentation, source slides, build scripts, and frozen weekly deliverables |
| `Hardware/` | Parts list, wiring references, integration prototype, and hardware test scripts |
| `Model Training/` | GTSRB, LISA, Mapillary, and combined-data preparation, training, evaluation, and reports; downloaded datasets are Git ignored |
| `Sign Cards/` | Printable 3 x 5 inch cards for the 12 U.S. sign classes and a US Letter print sheet |
| `Learning/` | Self-directed learning side-quests, separate from the main project |
| `setup.sh` | Installs basic Git and Python prerequisites on a Debian-based board |
| `AGENTS.md`, `CLAUDE.md` | Working agreements for AI assistants used on this repo |

### Weekly reports

Reports follow the TA's required template (`Weekly Reports/project_name.docx`). Everything at the top level of
`Weekly Reports/` is a live working copy:

- `Self_Driving_RC_Car.docx` / `.pdf` — the rolling report, rebuilt each week from `build_report.py` and submitted as PDF.
- `Self-Driving-RC-Car.pptx` — the rolling presentation deck (started Week 4). **Generated — do not hand-edit.**

The deck is assembled from one file per person in `Weekly Reports/slides/` (`0-title.pptx`, `1-ethan-wells.pptx`, …).
A `.pptx` is a binary file, so git cannot merge two people's edits to the same deck — everyone edits only their own
file, which makes conflicts impossible. Whoever assembles the deck runs `python3 assemble_deck.py` from inside
`Weekly Reports/`, which stitches the slide files in filename order into `Self-Driving-RC-Car.pptx`. See
`Weekly Reports/slides/README.md`.

Each week's frozen deliverables are archived in a `Week N/` subfolder — the dated report PDF and docx, plus the
dated presentation from Week 4 on:

```
Weekly Reports/
  build_report.py  context.md  project_name.docx       ← tooling + template
  assemble_deck.py                                     ← builds the deck from slides/
  slides/  0-title.pptx  1-ethan-wells.pptx  …         ← one file per person (edit yours)
  Self_Driving_RC_Car.docx / .pdf                      ← rolling report (working)
  Self-Driving-RC-Car.pptx                             ← rolling deck (generated)
  Week 1/ … Week 3/   frozen report .pdf + .docx
  Week 4/ … Week 7/   frozen report + frozen .pptx
```

See `Weekly Reports/context.md` for the full build/format guide.
