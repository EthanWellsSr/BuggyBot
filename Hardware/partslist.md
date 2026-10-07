# Parts List

Running list of hardware for the Self-Driving RC Car. Status: **Have** / **Ordered** / **Need** / **TBD**.

Wiring: current [Autonomous Car Schematic.png](Autonomous%20Car%20Schematic.png) · earlier Pico version [Schematic_with_pico.jpeg](Schematic_with_pico.jpeg).

| Component | Qty | Purpose | Status | Price (USD) | Date Purchased | Purchased By | Link |
|---|---|---|---|---|---|---|---|
| Raspberry Pi Compute Module 5 (4 GB, Lite) | 1 | Main compute — runs vision model | Have | 100.00 | 8/26 | Ethan Wells | [seeedstudio](https://www.seeedstudio.com/Raspberry-Pi-Compute-Module-CM5004000-p-6275.html) |
| Raspberry Pi Compute Module 5 IO Board | 1 | Carrier/prototyping board (M.2, camera, GPIO) | Have | 20.00 | 9/3 | Ethan Wells | [canakit](https://www.canakit.com/raspberry-pi-compute-module-5-io-board.html) |
| ZDE ZC505 CM5 aluminum heatsink + PWM fan | 1 | Secures CM5 to IO board; active cooling | Have | 11.99 | 9/16 | Ethan Wells | [amazon](https://www.amazon.com/dp/B0DT12D9F3) |
| iUniker 27W GaN USB-C PD power supply (5.1 V/5 A) | 1 | Bench power for CM5 IO Board and peripherals | Have | 10.89 | 9/16 | Ethan Wells | [amazon](https://www.amazon.com/dp/B0FHH9K47T) |
| Raspberry Pi Camera Module 3 Standard (12MP AF) | 1 | Reads traffic signs | Have | 29.25 | 9/7 | Abigail Duran | [adafruit 5657](https://www.adafruit.com/product/5657) |
| Adafruit ICM-20948 9-DoF IMU (STEMMA QT) | 1 | Heading / turns | Have | 19.95 | 9/7 | Ethan Bishop | [adafruit 4554](https://www.adafruit.com/product/4554) |
| STEMMA QT → male header cable, 150 mm | 1 | Wires IMU to CM5 header | Need | 0.95 | 9/9 | Ethan Bishop | [adafruit 4209](https://www.adafruit.com/product/4209) |
| Ultrasonic distance sensor, HC-SR04 (3.3 V) | 1 | Obstacle / wall distance (more later) | Have | 6.95 | 9/7 | Alexis Perez | [sparkfun](https://www.sparkfun.com/ultrasonic-distance-sensor-3-3v-hc-sr04.html) |
| Waveshare LCD1602 RGB (I²C) | 1 | Status display | Have | 17.99 | 9/9 | Abigail Duran | [amazon](https://www.amazon.com/dp/B095HBY7YP) |
| KIOXIA BG4 128 GB M.2 2230 NVMe SSD (KBG40ZNS128G) | 1 | Boot media | Have | 44.89 | 9/9 | Ethan Wells | [amazon](https://www.amazon.com/KIOXIA-Toshiba-128GB-KBG40ZNS128G-Package/dp/B09CR818J2) |
| UGREEN M.2 NVMe enclosure (USB) | 1 | Flash/interface the SSD from a PC | Have | 17.99 | 9/9 | Ethan Wells | [amazon](https://www.amazon.com/UGREEN-Enclosure-Tool-Free-Thunderbolt-Compatible/dp/B09T97Z7DM) |
| RPi 5 FPC camera cable (22-pin↔15-pin, 200 mm) | 1 | Connect Camera Module 3 to CM5 IO board | Need | 2.70 | 9/9 | Abigail Duran | [adafruit 5818](https://www.adafruit.com/product/5818) |
| CR2032 3V lithium coin cell | 1 | RTC/CMOS battery for CM5 IO Board (J4 holder) | Have | 6.29 | 9/14 | Ethan Wells | [amazon](https://www.amazon.com/Procter-Gamble-DURDL2032B4PK-Duracell-Lithium/dp/B009108SGS) |
| USB Wi-Fi dongle, TP-Link TL-WN725N (N150 nano, RTL8188EUS) | 1 | Wi-Fi for headless SSH on the vehicle (CM5 has no onboard wireless) | Have | 9.99 | 9/16 | Ethan Wells | [amazon](https://www.amazon.com/wifi-adapter-usb-pc-network/dp/B008IFXQFU) |
| RC car chassis | 1 | Vehicle frame | TBD | — | — | — | |
| DIANN drive set (2× 3–6 V TT motors, 2× wheels, L298N motor driver) | 1 | Propulsion, wheels, and dual-channel motor control | Ordered | 7.99 | 9/16 | Alexis Perez | [amazon](https://www.amazon.com/dp/B0BR7S1DQZ) |
| Waveshare Motor Driver HAT (PCA9685 + TB6612FNG, two DC motors) | 1 | Motor-control prototype | Have | 22.10 | 9/25 | Ethan Bishop | [amazon](https://www.amazon.com/dp/B07K7NP7C9) |
| LK COKOINO 4WD Robot HAT (DRV8833) | 1 | Motor-control prototype | Have | 9.99 | 9/25 | Ethan Bishop | [amazon](https://www.amazon.com/dp/B0D4VYW1PX) |
| Line sensors (model and quantity pending) | TBD | Detect the course line | Ordered | — | — | Alexis Perez | — |
| Steering servo | 1 | Steering | TBD | — | — | — | |
| Battery | 1 | Power source | TBD | — | — | — | |
| Battery charger | 1 | Charge the battery | TBD | — | — | — | |
| Custom carrier PCB | 1 | Final CM5 carrier board (spring) | TBD | — | — | — | |
| **Running total (priced items only)** | | | | **339.91** | | | |

Pricing may vary depending on current market; prices listed were from time of purchase.
The Week 6 report records bench tests of the camera, IMU, LCD, and both motor
controller HATs. The Week 7 slides record Alexis selecting and ordering line
sensors. The model, quantity, price, purchase date, and link for the line sensors
still need confirmation. The listed camera and IMU cables have not been matched
to the installed cables.

**Maybe later:** Raspberry Pi Pico as a real-time co-processor — only if the Pi 5's reaction time for the ultrasonic/motor timing isn't good enough.
