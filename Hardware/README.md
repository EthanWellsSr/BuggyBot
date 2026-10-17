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
three test scripts list their setup steps and wiring at the top of the file.

| Script | Tests | Interface |
| --- | --- | --- |
| [`sensor_test.py`](scripts/sensor_test.py) | HC-SR04 ultrasonic sensor; prints distance in cm | GPIO17 trigger, GPIO18 echo (gpiozero) |
| [`icm20948_test.py`](scripts/icm20948_test.py) | ICM-20948 IMU checks, then a live reading stream | I²C, address 0x69 or 0x68 |
| [`2WDmotor_hat_test.py`](scripts/2WDmotor_hat_test.py) | Motor-controller HATs: Cokoino (DRV8833), Waveshare (PCA9685 + TB6612), Adafruit | GPIO or I²C, chosen with `--board` |
| [`buggybot_integration.py`](scripts/buggybot_integration.py) | Integration prototype: camera capture and LCD output driven by **simulated** sign predictions | Camera Module 3, Waveshare LCD1602 (I²C) |

`scripts/buggybot_integration.py` expects Waveshare's LCD1602 demo library at
`/home/buggybot/LCD1602-RGB-Module-demo/Raspberry` on the CM5. It does not run
a trained model yet.

Lift the wheels off the ground before running the motor test.
