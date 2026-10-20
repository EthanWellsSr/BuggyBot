# Hardware

Parts, wiring references, bench-test scripts, and the custom-PCB design for
BuggyBot. Purchase and availability status is in [`partslist.md`](partslist.md).

## Wiring references

| File | Contents |
| --- | --- |
| [`Autonomous Car Schematic.png`](Schematics/Autonomous%20Car%20Schematic.png) | Current wiring schematic (CM5) |
| [`Schematic_with_pico.jpeg`](Schematics/Schematic_with_pico.jpeg) | Earlier version using a Raspberry Pi Pico; historical |
| [`cm5_io_board_week5.jpg`](Schematics/cm5_io_board_week5.jpg) | Photo of the CM5 booted on its IO Board (Week 5) |
| [`Navigation Ideas.pdf`](Navigation%20Ideas.pdf) | Navigation approach notes (Alexis Perez, 9/29) |
| [`BuggyBot KiCAD/`](BuggyBot%20KiCAD/) | KiCad project for the custom carrier PCB; see its [README](BuggyBot%20KiCAD/README.md) |

## Scripts

All scripts run on BuggyBot (the CM5), not on your development computer. The
test scripts list their setup steps and wiring at the top of the file.

| Script | Tests | Interface |
| --- | --- | --- |
| [`sensor_test.py`](scripts/sensor_test.py) | HC-SR04 ultrasonic sensor; prints distance in cm | GPIO17 trigger, GPIO18 echo (gpiozero) |
| [`icm20948_test.py`](scripts/icm20948_test.py) | ICM-20948 IMU checks, then a live reading stream | I²C, address 0x69 or 0x68 |
| [`2WDmotor_hat_test.py`](scripts/2WDmotor_hat_test.py) | Motor-controller HATs: Cokoino (DRV8833), Waveshare (PCA9685 + TB6612), Adafruit | GPIO or I²C, chosen with `--board` |
| [`Line Sensors.py`](scripts/Line%20Sensors.py) | TCRT5000 IR line sensors: reads the left and right course-line sensors and reports a lane action | GPIO17 left, GPIO27 right (gpiozero `DigitalInputDevice`) |
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
This first version does not search the frame for signs; that detection step is
next.

Lift the wheels off the ground before running the motor test.
