#!/usr/bin/env python3
"""
test_all_sensors.py - master bench test for BuggyBot's sensors and motor driver

Runs one short test per device, one after another, and prints a PASS/FAIL/SKIP
summary. A failure in one test never stops the others.

  line        TCRT5000 x2      GPIO17 left, GPIO27 right
  imu         ICM-20948        I2C 0x69 / 0x68
  camera      Camera Module 3  Picamera2
  lcd         Waveshare LCD1602 (I2C), text and RGB backlight
  motors      Motor driver HAT chosen with --board (runs 2WDmotor_hat_test.py's tests)

Setup is the union of the individual scripts (gpiozero, adafruit-circuitpython-icm20x,
picamera2, smbus2). A missing library only SKIPs that test.

Run (on BuggyBot):
  python3 test_all_sensors.py                   # everything
  python3 test_all_sensors.py --only imu camera
  python3 test_all_sensors.py --skip motors --no-motion
  python3 test_all_sensors.py --board waveshare --max 40

SAFETY: the motor test spins the motors. Lift the wheels off the ground first.

NOTE: the Cokoino HAT drives GPIO17 and GPIO27 (motor 1) as outputs, the same
pins the line sensors read. Tests run one at a time and release their pins, so
the software works, but both can't be wired at once. Check the schematic.

Alexis: "I updated GPIO pins for Line Sensors to Left = GPI020 and Right = GPIO21"
"""

import argparse
import importlib.util
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


def banner(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def load_script(filename):
    """Import a sibling script by path (works for 'Line Sensors.py', which has a space)."""
    spec = importlib.util.spec_from_file_location(Path(filename).stem.replace(" ", "_"), HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------- Line --
def wait_for_change(device, label, timeout=10.0):
    start = device.value
    print(f"  {label}: current output {start}. Move a dark line / your hand under it...")
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if device.value != start:
            return True
        time.sleep(0.02)
    return False


def test_line(args):
    mod = load_script("Line Sensors.py")
    sensors = mod.LaneSensors()
    try:
        left_ok = wait_for_change(sensors.left_sensor, f"Left (GPIO{mod.LEFT_GPIO})")
        right_ok = wait_for_change(sensors.right_sensor, f"Right (GPIO{mod.RIGHT_GPIO})")
    finally:
        sensors.cleanup()

    print(f"  Left changed: {left_ok} | Right changed: {right_ok}")
    if left_ok and right_ok:
        return PASS, "both sensors toggled"
    dead = [n for n, ok in (("left", left_ok), ("right", right_ok)) if not ok]
    return FAIL, f"{' and '.join(dead)} never changed: check wiring or the module's potentiometer"


# ----------------------------------------------------------------------- IMU --
def test_imu(args):
    mod = load_script("icm20948_test.py")  # exits with a message if the library is missing
    icm = mod.connect()  # exits if the chip isn't found
    ok, _bias = mod.static_test(icm)
    if not args.no_motion:
        ok &= mod.motion_test(icm)
    ok &= mod.rate_test(icm)
    return (PASS, "all checks passed") if ok else (FAIL, "see failed checks above")


# -------------------------------------------------------------------- Camera --
def test_camera(args):
    from picamera2 import Picamera2

    camera = Picamera2()
    try:
        camera.configure(camera.create_preview_configuration())
        camera.start()
        time.sleep(1.0)  # auto-exposure settle
        frame = camera.capture_array()
    finally:
        camera.close()

    brightness = float(frame.mean())
    print(f"  Frame {frame.shape[1]}x{frame.shape[0]}, mean brightness {brightness:.1f}/255")
    if brightness < 5:
        return FAIL, "frame is almost black: check the lens cap and ribbon cable"
    return PASS, f"{frame.shape[1]}x{frame.shape[0]} frame captured"


# --------------------------------------------------------------------- LCD --
# Same library location and 16x2 setup as buggybot_integration.py (which can't be
# imported here: it loads the model and camera and creates folders at import time).
LCD_LIBRARY_PATH = "/home/buggybot/LCD1602-RGB-Module-demo/Raspberry"


def test_lcd(args):
    sys.path.insert(0, LCD_LIBRARY_PATH)
    import RGB1602

    lcd = RGB1602.RGB1602(16, 2)
    try:
        for name, color in (("RED", (255, 0, 0)), ("GREEN", (0, 255, 0)), ("BLUE", (0, 0, 255))):
            lcd.clear()
            lcd.setRGB(*color)
            lcd.setCursor(0, 0)
            lcd.printout("BuggyBot LCD"[:16])
            lcd.setCursor(0, 1)
            lcd.printout(f"Backlight {name}"[:16])
            time.sleep(1.5)
        ans = input("  Did the text show on both lines and the backlight go red, green, blue? [y/n] ").strip().lower()
    finally:
        lcd.clear()
        lcd.setRGB(0, 0, 0)

    if ans == "y":
        return PASS, "text and backlight colors confirmed"
    if ans == "n":
        return FAIL, "check I2C wiring/power and the LCD's contrast and address"
    return SKIP, "not confirmed"


# -------------------------------------------------------------------- Motors --
def test_motors(args):
    mod = load_script("2WDmotor_hat_test.py")
    board = mod.BOARDS[args.board]
    nums = args.motors or sorted(board["motors"])
    bad = [n for n in nums if n not in board["motors"]]
    if bad:
        return FAIL, f"{board['name']} has motors {sorted(board['motors'])}; got {bad}"

    # The hardware classes read these fields from the motor script's argparse result.
    hw_args = argparse.Namespace(addr=None, bus=1, freq=None)
    hw = (mod.GPIOHardware if board["type"] == "gpio" else mod.I2CHardware)(board, hw_args)
    try:
        motors = {n: hw.make_motor(n, board["motors"][n], False) for n in nums}
        input("  Lift the wheels off the ground, turn motor power on, then press Enter...")
        max_speed = max(1, min(100, args.max))
        results = {f"Motor {n}": mod.test_motor(m, max_speed, 10, 0.2, 1.5) for n, m in motors.items()}
        if len(motors) > 1:
            results["All together"] = mod.test_all_together(list(motors.values()), max_speed, 1.5)
    finally:
        hw.all_off()
        hw.close()
        print("  All motors stopped.")

    failed = [name for name, r in results.items() if r == "FAIL"]
    if failed:
        return FAIL, f"{', '.join(failed)} did not behave: check battery, HAT power switch, motor terminals"
    if all(r == "SKIPPED" for r in results.values()):
        return SKIP, "every motor test skipped"
    return PASS, f"{board['name']}: {len(motors)} motor(s) OK"


TESTS = {
    "line": test_line,
    "imu": test_imu,
    "camera": test_camera,
    "lcd": test_lcd,
    "motors": test_motors,
}


# ---------------------------------------------------------------------- Main --
def run(name, args):
    banner(f"{name.upper()}")
    try:
        return TESTS[name](args)
    except (ImportError, SystemExit) as e:
        # SystemExit comes from the individual scripts' own missing-library / no-device exits.
        reason = e.code if isinstance(e, SystemExit) else e
        return SKIP, f"missing library or device: {reason}"
    except KeyboardInterrupt:
        return SKIP, "interrupted"
    except Exception as e:
        return FAIL, f"{type(e).__name__}: {e}"


def main():
    p = argparse.ArgumentParser(description="Test BuggyBot's sensors and motor driver.")
    p.add_argument("--only", nargs="+", choices=TESTS, help="run just these tests")
    p.add_argument("--skip", nargs="+", choices=TESTS, default=[], help="skip these tests")
    p.add_argument("--no-motion", action="store_true", help="IMU: skip the interactive motion test")
    p.add_argument("--board", choices=["cokoino", "waveshare", "adafruit"], default="cokoino",
                   help="motor HAT to test (default cokoino)")
    p.add_argument("--motors", type=int, nargs="+", help="motor numbers to test (default: all)")
    p.add_argument("--max", type=int, default=60, help="motors: max speed %% (default 60)")
    args = p.parse_args()

    names = [n for n in (args.only or TESTS) if n not in args.skip]
    results = {name: run(name, args) for name in names}

    banner("SUMMARY")
    for name, (status, detail) in results.items():
        print(f"  [{status}] {name:<11} {detail}")
    sys.exit(1 if any(s == FAIL for s, _ in results.values()) else 0)


if __name__ == "__main__":
    main()
