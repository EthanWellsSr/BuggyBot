# Hardware

Parts, wiring references, bench-test scripts, and the custom-PCB design for
BuggyBot. Purchase and availability status is in [`partslist.md`](partslist.md).

## Setup scripts

| Script | Runs on | Purpose |
|---|---|---|
| [`setup.sh`](../setup.sh) | Development computer | Git, Python, pip, venv — shared dev prerequisites |
| [`Hardware/setup.sh`](setup.sh) | BuggyBot (the CM5) | Picamera2, OpenCV, NumPy, SMBus, GPIOZero, and the LiteRT virtual environment (`~/buggybot-venv`) |

The root `setup.sh` does **not** run on the Pi — `apt-get` isn't available on macOS, and the Pi doesn't need TensorFlow/Keras for inference (it uses LiteRT).

## Wiring references

| File | Contents |
| --- | --- |
| [`Autonomous Car Schematic.png`](Schematics/Autonomous%20Car%20Schematic.png) | Wiring schematic (CM5, 10/17); out of date: still shows the HC-SR04 and lacks the line sensors and motor HAT |
| [`Schematic_with_pico.jpeg`](Schematics/Schematic_with_pico.jpeg) | Earlier version using a Raspberry Pi Pico; historical |
| [`cm5_io_board_week5.jpg`](Schematics/cm5_io_board_week5.jpg) | Photo of the CM5 booted on its IO Board (Week 5) |
| [`Navigation Ideas.pdf`](Navigation%20Ideas.pdf) | Navigation approach notes (Alexis Perez, 9/29) |
| [`BuggyBot KiCAD/`](BuggyBot%20KiCAD/) | KiCad project for the custom carrier PCB; see its [README](BuggyBot%20KiCAD/README.md) |

## 3D prints

| File | Contents |
| --- | --- |
| [`camera_bracket.py`](3D%20Prints/camera_bracket.py) | Generates `camera_bracket.stl` (no dependencies; run with `python3` on your development computer): a Camera Module 3 bracket that bolts to IO board hole H7 behind CAM/DISP 0 with one M2.5 screw and to the camera's two holes on one side with M2 self-tapping screws. Positions come from `CM5IO.kicad_pcb`; measure the board before printing |
| [`camera_bracket.stl`](3D%20Prints/camera_bracket.stl) | Generated print file; print foot down, no supports |

## Scripts

All scripts in this section run on BuggyBot (the CM5), not on your development computer. The
test scripts list their setup steps and wiring at the top of the file.

| Script | Tests | Interface |
| --- | --- | --- |
| [`icm20948_test.py`](scripts/icm20948_test.py) | ICM-20948 IMU checks, then a live reading stream | I²C, address 0x69 or 0x68 |
| [`motor_hat_test.py`](scripts/motor_hat_test.py) | Motor-controller HATs, chosen with `--board`: Cokoino 4WD Robot HAT (DRV8833; default) or Waveshare Motor Driver HAT (2WD, PCA9685 + TB6612). Ramps both directions, interactive mode (`-i`), bus scan (`--scan`, Waveshare only) | Cokoino: GPIO12/13 sleep, 16/17/22–27 inputs · Waveshare: I²C 0x40 |
| [`Line Sensors.py`](scripts/Line%20Sensors.py) | TCRT5000 IR line sensors: reads the left and right course-line sensors and reports a lane action | GPIO20 left, GPIO21 right (gpiozero `DigitalInputDevice`) |
| [`test_all_sensors.py`](scripts/test_all_sensors.py) | Integration test before PCB sign-off (Ethan Bishop's master test, extended 10/27): pin-map clash check, I²C scan, line sensors, IMU, motors, the full sign pipeline (camera, LCD, and the sign demo checked automatically; any card, with fps and inference time), then a stress run with everything at once that checks for under-voltage, I²C errors, line-sensor noise, and frame-rate drop. Saves a JSON report to [`integration_reports/`](integration_reports/); commit the reports worth keeping as the PCB sign-off record (file names use the Pi's clock). Run with `~/buggybot-venv/bin/python`; options `--only`, `--skip`, `--board` (cokoino default, or waveshare), `--motors` (default 1 2 on either board), `--stress-seconds` | GPIO20/21, I²C (IMU, LCD, Waveshare HAT), CSI camera, Cokoino GPIO pins |

The live sign demo is in [`Model Training/OpenCV/`](../Model%20Training/OpenCV/README.md).
Run `Hardware/setup.sh` first for its packages and the LiteRT venv.

### Integration test result (10/28)

All seven stages passed on the Cokoino HAT, powered from the Pi with no
batteries and the wheels off the ground: I²C found the LCD (0x3E, backlight
0x60) and IMU (0x69), both line sensors toggled, the pipeline read a card at
98% with 1.9 ms mean inference and 36 fps, and the 120 s stress run held 30 fps
with no I²C errors and no under-voltage. Battery power and a loaded drivetrain
are still untested. See the [report](integration_reports/integration_20261028_192332.json).

Lift the wheels off the ground before running the motor test.
