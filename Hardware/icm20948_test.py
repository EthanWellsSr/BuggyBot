#!/usr/bin/env python3
"""
Adafruit ICM-20948 9-DoF IMU test script (Raspberry Pi, I2C)

Wiring (STEMMA QT / Qwiic or header pins):
    Board VIN -> Pi 3.3V (pin 1)
    Board GND -> Pi GND  (pin 6)
    Board SCL -> Pi SCL  (GPIO3, pin 5)
    Board SDA -> Pi SDA  (GPIO2, pin 3)

Setup:
    sudo raspi-config        # Interface Options -> I2C -> Enable, then reboot
    pip3 install adafruit-circuitpython-icm20x --break-system-packages
    i2cdetect -y 1           # should show 69 (default) or 68 (ADR jumper closed)

Run:
    python3 icm20948_test.py            # full test, then live stream
    python3 icm20948_test.py --stream   # skip checks, just stream readings
"""

import argparse
import math
import sys
import time

try:
    import board
    import busio
    import adafruit_icm20x
except ImportError as e:
    sys.exit(
        f"Missing library ({e}).\n"
        "Install with: pip3 install adafruit-circuitpython-icm20x --break-system-packages"
    )

G = 9.80665
ADDRESSES = (0x69, 0x68)


def banner(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def result(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")
    return ok


def scan_bus(i2c):
    while not i2c.try_lock():
        pass
    try:
        return i2c.scan()
    finally:
        i2c.unlock()


def connect():
    banner("1. I2C connection")
    i2c = busio.I2C(board.SCL, board.SDA)
    found = scan_bus(i2c)
    print(f"  Devices on bus: {[hex(a) for a in found] or 'none'}")

    for addr in ADDRESSES:
        if addr in found:
            try:
                icm = adafruit_icm20x.ICM20948(i2c, address=addr)
                result("ICM-20948 detected", True, f"at {hex(addr)}")
                return icm
            except Exception as e:  # wrong chip ID, magnetometer not responding, etc.
                result(f"Init at {hex(addr)}", False, str(e))

    result("ICM-20948 detected", False, "check wiring / power / I2C enabled")
    sys.exit(1)


def sample(icm, n=200, delay=0.01):
    acc, gyr, mag = [], [], []
    for _ in range(n):
        acc.append(icm.acceleration)
        gyr.append(icm.gyro)
        mag.append(icm.magnetic)
        time.sleep(delay)
    return acc, gyr, mag


def mean(vectors):
    n = len(vectors)
    return tuple(sum(v[i] for v in vectors) / n for i in range(3))


def std(vectors):
    m = mean(vectors)
    n = len(vectors)
    return tuple(math.sqrt(sum((v[i] - m[i]) ** 2 for v in vectors) / n) for i in range(3))


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def fmt(v, p=3):
    return "(" + ", ".join(f"{x:+.{p}f}" for x in v) + ")"


def static_test(icm):
    banner("2. Static test — keep the sensor still and flat")
    time.sleep(1)
    acc, gyr, mag = sample(icm)
    passed = True

    a_mean, a_std = mean(acc), std(acc)
    a_mag = norm(a_mean)
    print(f"  Accel mean  (m/s^2): {fmt(a_mean)}   |a| = {a_mag:.3f}")
    print(f"  Accel noise (m/s^2): {fmt(a_std)}")
    passed &= result("Gravity magnitude ~9.81", abs(a_mag - G) < 0.6, f"({a_mag:.2f})")
    passed &= result("Accel noise low", max(a_std) < 0.15)

    g_mean, g_std = mean(gyr), std(gyr)
    print(f"  Gyro bias   (rad/s): {fmt(g_mean, 4)}")
    print(f"  Gyro noise  (rad/s): {fmt(g_std, 4)}")
    passed &= result("Gyro bias small at rest", max(abs(x) for x in g_mean) < 0.05)
    passed &= result("Gyro noise low", max(g_std) < 0.02)

    m_mean = mean(mag)
    m_mag = norm(m_mean)
    print(f"  Mag mean    (uT):    {fmt(m_mean, 2)}   |B| = {m_mag:.1f}")
    # Earth's field is ~25-65 uT; motors/metal nearby will skew this.
    passed &= result("Mag field in Earth range", 15 < m_mag < 100, f"({m_mag:.1f} uT)")
    passed &= result("Mag not stuck at zero", m_mag > 1.0)

    # Which axis is "up"?
    axis = max(range(3), key=lambda i: abs(a_mean[i]))
    sign = "+" if a_mean[axis] > 0 else "-"
    print(f"  Gravity is along {sign}{'XYZ'[axis]} axis")
    return passed, g_mean


def motion_test(icm, duration=4.0):
    banner("3. Motion test — rotate/tilt the sensor for 4 seconds")
    for i in range(3, 0, -1):
        print(f"  Starting in {i}...", end="\r")
        time.sleep(1)
    print("  GO! Rotate it around all axes...     ")

    peak = [0.0, 0.0, 0.0]
    acc_range = [[1e9, -1e9] for _ in range(3)]
    end = time.monotonic() + duration
    while time.monotonic() < end:
        g = icm.gyro
        a = icm.acceleration
        for i in range(3):
            peak[i] = max(peak[i], abs(g[i]))
            acc_range[i][0] = min(acc_range[i][0], a[i])
            acc_range[i][1] = max(acc_range[i][1], a[i])
        time.sleep(0.01)

    print(f"  Peak gyro (rad/s): {fmt(peak)}")
    passed = True
    for i, ax in enumerate("XYZ"):
        passed &= result(f"Gyro {ax} responded", peak[i] > 0.5, f"({peak[i]:.2f} rad/s)")
    for i, ax in enumerate("XYZ"):
        span = acc_range[i][1] - acc_range[i][0]
        passed &= result(f"Accel {ax} changed", span > 3.0, f"(span {span:.1f} m/s^2)")
    return passed


def rate_test(icm, n=500):
    banner("4. Read-rate test")
    t0 = time.perf_counter()
    for _ in range(n):
        icm.acceleration
        icm.gyro
        icm.magnetic
    dt = time.perf_counter() - t0
    hz = n / dt
    print(f"  {n} full 9-axis reads in {dt:.2f}s -> {hz:.0f} Hz")
    return result("Read rate usable (>50 Hz)", hz > 50)


def stream(icm, gyro_bias=(0.0, 0.0, 0.0)):
    banner("Live stream (Ctrl+C to stop)")
    print("  Heading is tilt-uncompensated — keep the board flat for a meaningful value.\n")
    try:
        while True:
            a = icm.acceleration
            g = tuple(g_i - b for g_i, b in zip(icm.gyro, gyro_bias))
            m = icm.magnetic
            roll = math.degrees(math.atan2(a[1], a[2]))
            pitch = math.degrees(math.atan2(-a[0], math.hypot(a[1], a[2])))
            heading = (math.degrees(math.atan2(m[1], m[0])) + 360) % 360
            print(
                f"A {fmt(a, 2)} m/s^2 | G {fmt(g, 2)} rad/s | M {fmt(m, 1)} uT | "
                f"roll {roll:+6.1f}  pitch {pitch:+6.1f}  hdg {heading:5.1f}",
                end="\r",
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n  Stopped.")


def main():
    parser = argparse.ArgumentParser(description="ICM-20948 test")
    parser.add_argument("--stream", action="store_true", help="skip tests, only stream data")
    parser.add_argument("--no-motion", action="store_true", help="skip the interactive motion test")
    args = parser.parse_args()

    icm = connect()

    if args.stream:
        stream(icm)
        return

    ok, bias = static_test(icm)
    if not args.no_motion:
        ok &= motion_test(icm)
    ok &= rate_test(icm)

    banner("RESULT: " + ("ALL TESTS PASSED" if ok else "SOME TESTS FAILED"))
    input("\nPress Enter to start the live stream (Ctrl+C to quit)...")
    stream(icm, gyro_bias=bias)


if __name__ == "__main__":
    main()
