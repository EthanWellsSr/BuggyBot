# BuggyBot

University of Houston–Clear Lake (UHCL) Senior Project, CENG 4265. The course
deliverables use the project title **Self Driving RC Car**; BuggyBot is the
repository and vehicle name.

BuggyBot is an autonomous car project intended to follow a controlled course and obey
traffic signs. The fall scope is a stationary sign-recognition system; the
spring scope is the autonomous vehicle.

## Current state

- The bench platform uses a Raspberry Pi Compute Module 5 (CM5) on its IO Board,
  booting Raspberry Pi OS Lite from an M.2 NVMe SSD. USB Wi-Fi supplies network
  access because this CM5 Lite has no onboard wireless.
- [`Model Training/OpenCV/pi_sign_detection_demo.py`](Model%20Training/OpenCV/)
  is the live sign demo on the CM5. It finds sign regions with OpenCV,
  classifies them with the combined model, and shows the confirmed sign on the
  LCD. In the final test, 60 of 60 LCD outputs were correct (10 printed sign
  classes, 3 times each over two runs, one room).
- [`Hardware/scripts/test_all_sensors.py`](Hardware/scripts/test_all_sensors.py)
  is the integration test before PCB sign-off. On 10/28 all seven stages passed
  on the Cokoino HAT (pins, I²C, line sensors, IMU, motors, sign pipeline, and a
  120 s stress run with everything at once), powered from the Pi with the wheels
  off the ground. Battery power and a loaded drivetrain are untested. Reports are
  in [`Hardware/integration_reports/`](Hardware/integration_reports/). Nothing
  drives the vehicle yet.
- TensorFlow classifiers have been trained on GTSRB, LISA, Mapillary, and a
  combined LISA+Mapillary dataset. Their models and results are in this repo.
- A ROS 2 node architecture for the vehicle (camera, sign detector, line sensor,
  IMU, behavior, motor driver, LCD, teleop) has been drafted. ROS 2 is installed
  under WSL on a development machine; it is not running on the CM5.

## Hardware

- **Compute and storage:** Raspberry Pi CM5 (4 GB Lite), CM5 IO Board, M.2 NVMe
- **Networking:** USB Wi-Fi dongle for headless SSH
- **Vision and sensing:** Camera Module 3, ICM-20948 IMU (the HC-SR04 ultrasonic sensor is no longer used)
- **Course sensing:** TCRT5000 IR line sensors (received); a line-sensor script that
  reads the left (GPIO20) and right (GPIO21) sensors is in `Hardware/scripts/Line Sensors.py`
- **Output and motion:** I²C LCD; two motor-controller HATs are supported: the
  Waveshare Motor Driver HAT (2WD, I²C) and the Cokoino 4WD Robot HAT (GPIO).
  Vehicle motor control is being developed
- **Chassis:** EMOZNY Emo smart robot car chassis kit (2 DC gear motors with
  speed encoders, battery box) has been received
- **Custom PCB:** a KiCad carrier-board design, derived from the CM5 IO Board, is
  in progress in [`Hardware/BuggyBot KiCAD/`](Hardware/BuggyBot%20KiCAD/)

The [parts list](Hardware/partslist.md) records purchase and availability
status. Wiring references and hardware test scripts are in [`Hardware/`](Hardware/);
see its [README](Hardware/README.md).

## Traffic-sign models

The image classifiers use 32×32 sign crops. On the CM5, the live demo in
[`Model Training/OpenCV/`](Model%20Training/OpenCV/README.md) locates signs in
each camera frame, crops them without using the known class, and runs the
combined TFLite model on each crop.

| Dataset and model | Classes | Prepared crops | Held-out result | Status |
| --- | ---: | ---: | --- | --- |
| GTSRB, German signs | 43 | See [training guide](Model%20Training/README.md) | 95.79% top-1 on 12,630 test images | Model and evaluation committed |
| LISA, selected US signs | 12 | 6,097 | 89.90% top-1 on 584 test crops | Model and report committed |
| Mapillary, mapped to the same 12 classes | 12 | 3,449 | 92.59% top-1 on 432 test crops | Model and report committed |
| Combined LISA+Mapillary | 12 | 9,546 | 99.31% top-1 on 1,016 combined test crops | Model, training report, and same-set comparison committed |

The separate LISA and Mapillary percentages use **different test sets** and do
not rank those models. The [same-set comparison](Model%20Training/reports/combined_model_comparison.md)
evaluates all three US-sign models on the 1,016 combined test crops. The
combined set preserves each source's split but does not establish physical-sign
independence across datasets. The Mapillary test set has only two speed-limit-65
crops.

On BuggyBot's own camera, the combined model classified **all 329** cropped
photos of the printed [sign cards](Sign%20Cards/README.md) correctly (10
classes, three lighting conditions, about 30 distinct setups). The LISA and
Mapillary models scored 47.7% and 79.9%. These crops were placed with
knowledge of each sign's class. Through the car's own detector (the live
demo), 60 of 60 LCD outputs were correct in one room; distance, angle, other
lighting are still unmeasured; CM5 inference averaged 1.9 ms per crop (36 fps). See the [model training guide](Model%20Training/README.md) for the
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
| `Hardware/` | Parts list, wiring references, hardware test scripts, integration test reports, and the KiCad custom-PCB project |
| `Model Training/` | GTSRB, LISA, Mapillary, and combined-data preparation, training, evaluation, and reports; the live Pi sign demo in `OpenCV/`; downloaded datasets are Git ignored |
| `Sign Cards/` | Printable 3 x 5 inch cards for the 12 U.S. sign classes, a US Letter print sheet, and cropped camera test photos |
| `Learning/` | Self-directed learning side-quests, separate from the main project |
| `setup.sh` | Installs Git, Python, pip, and venv on your development computer |
| `Hardware/setup.sh` | Installs Picamera2, OpenCV, NumPy, SMBus, GPIOZero, and the LiteRT venv on BuggyBot (the CM5) |
| `AGENTS.md` | Working agreements for AI assistants used on this repo |
| `.github/` | GitHub Actions CI, run on every push: Python scripts compile, `ruff` bug lint, sign-demo regression on the 329 test crops, integration-test pin map for both motor HATs, and Markdown link check (helper scripts in `.github/scripts/`) |

### Weekly reports

Weekly reports and the presentation deck are built from `Weekly Reports/`;
see [`Weekly Reports/context.md`](Weekly%20Reports/context.md) for the build
and format guide, and [`slides/README.md`](Weekly%20Reports/slides/README.md)
for how each person edits their own slides.
