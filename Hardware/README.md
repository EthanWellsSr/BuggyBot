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
| [`Autonomous Car Schematic.png`](Schematics/Autonomous%20Car%20Schematic.png) | Current wiring schematic (CM5) |
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
| [`2WDmotor_hat_test.py`](scripts/2WDmotor_hat_test.py) | Motor-controller HATs, chosen with `--board`: Waveshare Motor Driver HAT (2WD, PCA9685 + TB6612; default) or Cokoino 4WD Robot HAT (DRV8833). Ramps both directions, interactive mode (`-i`), bus scan (`--scan`) | Waveshare: I²C 0x40 · Cokoino: GPIO12/13 sleep, 16/17/22–27 inputs |
| [`Line Sensors.py`](scripts/Line%20Sensors.py) | TCRT5000 IR line sensors: reads the left and right course-line sensors and reports a lane action | GPIO20 left, GPIO21 right (gpiozero `DigitalInputDevice`) |
| [`test_all_sensors.py`](scripts/test_all_sensors.py) | Integration test before PCB sign-off (Ethan Bishop's master test, extended 10/27): pin-map clash check, I²C scan, line sensors, IMU, motors, the full sign pipeline (camera, LCD, and the sign demo checked automatically; any card, with fps and inference time), then a stress run with everything at once that checks for under-voltage, I²C errors, line-sensor noise, and frame-rate drop. Saves a JSON report to `~/buggybot_integration_reports/`; copy reports worth keeping into [`integration_reports/`](integration_reports/) as the PCB sign-off record (file names use the Pi's clock). Run with `~/buggybot-venv/bin/python`; options `--only`, `--skip`, `--board` (cokoino default, or waveshare), `--motors` (default 1 2 on either board), `--stress-seconds` | GPIO20/21, I²C (IMU, LCD, Waveshare HAT), CSI camera, Cokoino GPIO pins |
| [`buggybot_integration.py`](scripts/buggybot_integration.py) | Live sign test: classifies a fixed square region of each camera frame with the combined model and shows the sign on the LCD | Camera Module 3 (Picamera2), Waveshare LCD1602 (I²C) |

### Live sign test

`scripts/buggybot_integration.py` loads `Model Training/models/combined_model.tflite`
and its label file from the repository, and Waveshare's LCD1602 demo library from
`/home/buggybot/LCD1602-RGB-Module-demo/Raspberry`. It needs Picamera2, OpenCV,
and the LiteRT runtime. On the CM5 they are installed in a virtual environment
that can also see the system packages:

```bash
sudo apt install -y python3-picamera2 python3-opencv python3-numpy python3-smbus
```

```bash
python3 -m venv --system-site-packages ~/buggybot-venv && ~/buggybot-venv/bin/pip install ai-edge-litert
```

```bash
~/buggybot-venv/bin/python ~/BuggyBot/Hardware/scripts/buggybot_integration.py
```

Hold the sign card so it fills the green square drawn on each saved frame in
`~/buggybot_images/` (about 18% of the frame width, near the center). The box
position and size, the confidence threshold, and manual or automatic capture are
set at the top of the script. Below the threshold the LCD shows `SCANNING...`.
This script does not search the frame for signs. The live sign demo in
[`Model Training/OpenCV/`](../Model%20Training/OpenCV/README.md) does: it finds
signs anywhere in the frame, streams video to a browser, and colors the LCD by
sign.

Lift the wheels off the ground before running the motor test.
