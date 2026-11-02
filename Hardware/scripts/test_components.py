#!/usr/bin/env python3
"""
test_components.py - BuggyBot per-component test, run before the custom PCB is sent off

The question this answers: does each device work ON ITS OWN, on the pins and
buses the PCB will use? Each stage tests one device with nothing else running,
so a failure here points at that device or its wiring. Whether everything works
AT THE SAME TIME (power dips, motor noise on I2C and GPIO) is stress_test.py's
job; run this first, then that.

Stages, in order (a failure never stops later stages):

  pins      PIN_MAP has no GPIO used by two devices        (no hardware needed)
  i2c       every expected I2C device answers               I2C bus 1
  line      TCRT5000 x2 toggle when a line passes under    GPIO20 left, GPIO21 right
  imu       ICM-20948 still / motion / read-rate checks     I2C 0x69 or 0x68
  motors    each motor spins both ways                      HAT chosen with --board
  pipeline  camera, LCD, and the sign demo read any card     Camera Module 3, LCD1602

Every run saves a JSON report (results + measurements) to Hardware/integration_reports/
in the repository, so the team can commit it as the record for approving the PCB.

Setup is the union of the individual scripts plus the sign demo's: gpiozero,
adafruit-circuitpython-icm20x, smbus2, picamera2, OpenCV, and LiteRT. Run the
pipeline stage with the LiteRT venv:

  ~/buggybot-venv/bin/python test_components.py                  # everything
  ~/buggybot-venv/bin/python test_components.py --only pins i2c  # quick wiring check
  ~/buggybot-venv/bin/python test_components.py --board waveshare --max 40

SAFETY: the motors stage spins the motors. Lift the wheels off the ground first.

NOTE: the line sensors moved from GPIO17/27 to GPIO20/21 (10/27) so they no
longer share pins with the Cokoino HAT's motor 1 outputs (GPIO17/27). The
`pins` stage exists so that kind of clash is caught before the PCB is built.
"""

import argparse
import datetime
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEMO = REPO / "Model Training" / "OpenCV" / "pi_sign_detection_demo.py"

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"

# Measurements collected by the stages; written into the JSON report.
METRICS = {}

# ------------------------------------------------------------------ Pin map --
# Every GPIO (BCM numbering) each device uses on BuggyBot today. This must match
# the KiCad schematic in Hardware/BuggyBot KiCAD/ -- check it against the PCB
# before sign-off. The camera uses the CSI connector, not GPIO.
I2C_PINS = {"i2c SDA": 2, "i2c SCL": 3}  # IMU, LCD, and the Waveshare motor HAT
LINE_PINS = {"line left": 20, "line right": 21}

# I2C addresses that must answer on bus 1. The LCD1602 RGB's text controller
# is 0x3E on every board revision; its backlight chip's address varies by
# revision, so only the text controller is required. The scan records every
# address it finds in the report.
IMU_ADDRESSES = (0x69, 0x68)
LCD_ADDRESS = 0x3E


def motor_pins(board_name, board):
    """GPIOs the motor HAT claims: its I2C pins, or its direct-drive pins."""
    if board["type"] == "i2c":
        return {}  # shares I2C_PINS
    pins = {}
    for n, (sleep, in1, in2) in board["motors"].items():
        # One driver chip's sleep pin serves two motors, so name it by pin, once.
        pins[f"{board_name} sleep GPIO{sleep}"] = sleep
        pins[f"{board_name} M{n} in1"] = in1
        pins[f"{board_name} M{n} in2"] = in2
    return pins


def banner(text):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def load_script(path):
    """Import a script by path (works for 'Line Sensors.py' and paths with spaces)."""
    path = Path(path)
    if not path.is_absolute():
        path = HERE / path
    spec = importlib.util.spec_from_file_location(path.stem.replace(" ", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



# --------------------------------------------------------------------- Pins --
def test_pins(args):
    board = load_script("motor_hat_test.py").BOARDS[args.board]
    pin_map = {**I2C_PINS, **LINE_PINS, **motor_pins(args.board, board)}
    users = {}
    for name, pin in pin_map.items():
        users.setdefault(pin, []).append(name)
    clashes = {pin: names for pin, names in users.items() if len(names) > 1}
    for pin, names in sorted(users.items()):
        print(f"  GPIO{pin:<3} {', '.join(names)}")
    METRICS["pin_map"] = {name: pin for name, pin in pin_map.items()}
    if clashes:
        return FAIL, "; ".join(f"GPIO{p} used by {', '.join(n)}" for p, n in clashes.items())
    return PASS, f"{len(pin_map)} pin assignments, no clashes (compare with the KiCad schematic)"


# ---------------------------------------------------------------------- I2C --
def test_i2c(args):
    mod = load_script("motor_hat_test.py")
    board = mod.BOARDS[args.board]
    found = mod.scan_bus(1)
    METRICS["i2c_addresses"] = [f"0x{a:02X}" for a in found]
    missing = []
    if not any(a in found for a in IMU_ADDRESSES):
        missing.append("IMU (0x69/0x68)")
    if LCD_ADDRESS not in found:
        missing.append(f"LCD (0x{LCD_ADDRESS:02X})")
    if board["type"] == "i2c" and board["addr"] not in found:
        missing.append(f"{board['name']} (0x{board['addr']:02X})")
    if missing:
        return FAIL, f"not answering: {', '.join(missing)}"
    return PASS, f"found {', '.join(METRICS['i2c_addresses'])}"


# --------------------------------------------------------------------- Line --
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


# ---------------------------------------------------------------------- IMU --
def test_imu(args):
    mod = load_script("icm20948_test.py")  # exits with a message if the library is missing
    icm = mod.connect()  # exits if the chip isn't found
    ok, _bias = mod.static_test(icm)
    if not args.no_motion:
        ok &= mod.motion_test(icm)
    ok &= mod.rate_test(icm)
    return (PASS, "all checks passed") if ok else (FAIL, "see failed checks above")


# ------------------------------------------------------------------- Motors --
def open_motors(args):
    """Return (motor script module, hardware, {number: motor}) for --board / --motors."""
    mod = load_script("motor_hat_test.py")
    board = mod.BOARDS[args.board]
    # BuggyBot drives with motors 1 and 2 on either board; --motors overrides.
    nums = args.motors or [1, 2]
    bad = [n for n in nums if n not in board["motors"]]
    if bad:
        raise ValueError(f"{board['name']} has motors {sorted(board['motors'])}; got {bad}")
    # The hardware classes read these fields from the motor script's argparse result.
    hw_args = argparse.Namespace(addr=None, bus=1, freq=None)
    hw = (mod.GPIOHardware if board["type"] == "gpio" else mod.I2CHardware)(board, hw_args)
    motors = {n: hw.make_motor(n, board["motors"][n], False) for n in nums}
    return mod, hw, motors


def test_motors(args):
    mod, hw, motors = open_motors(args)
    try:
        input("  Lift the wheels off the ground, turn motor power on, then press Enter...")
        max_speed = max(1, min(100, args.max))
        results = {f"Motor {n}": mod.test_motor(m, max_speed, 10, 0.2) for n, m in motors.items()}
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
    return PASS, f"{len(motors)} motor(s) OK"


# ----------------------------------------------------------------- Pipeline --
class SignPipeline:
    """The sign demo's detection steps (camera -> OpenCV -> model -> checks), reused
    from pi_sign_detection_demo.py so this test exercises exactly the demo's code."""

    def __init__(self, width=1280, height=720):
        self.d = load_script(DEMO)
        self.labels = self.d.LABELS_PATH.read_text().split()
        self.interpreter = self.d.load_interpreter(self.d.MODEL_PATH)
        from picamera2 import Picamera2
        self.camera = Picamera2()
        self.camera.configure(self.camera.create_video_configuration(
            main={"size": (width, height), "format": "RGB888"}))
        self.camera.start()
        time.sleep(2)  # exposure settle
        self.inference_s = []

    def step(self, threshold=0.85):
        """Process one frame; return the best (label, confidence) or None."""
        frame = self.camera.capture_array("main")
        self.last_frame = frame
        matches = []
        for box in self.d.make_candidates(frame, 8):
            crop = self.d.crop_square(frame, box)
            if crop.size == 0:
                continue
            t0 = time.perf_counter()
            label, confidence = self.d.classify(self.interpreter, self.labels, crop)
            self.inference_s.append(time.perf_counter() - t0)
            if confidence >= threshold and self.d.shape_matches(crop, label):
                matches.append((box, label, confidence))
        matches = [m for m in matches
                   if not any(o is not m and self.d.contains(o[0], m[0]) for o in matches)]
        if not matches:
            return None
        _, label, confidence = max(matches, key=lambda m: m[2])
        return label, confidence

    def close(self):
        self.camera.stop()
        self.camera.close()


def ms(seconds):
    return round(1000 * seconds, 1)


def test_pipeline(args):
    """Camera, LCD, and the sign demo's detection, judged without questions.

    Camera: frames arrive at the expected size and are not blank (a dead or
    covered sensor gives near-zero brightness variation).
    LCD: every write must be acknowledged on I2C by both of its chips (text and
    backlight); a missing or unpowered LCD raises "Remote I/O error". This
    proves the LCD received the text, not that the pixels are readable.
    Detection: any sign the demo confirms on 3 consecutive frames is accepted;
    the demo's shape check already rejects reads that don't match the card.
    """
    problems = []
    pipe = SignPipeline()
    d = pipe.d
    try:
        frame = pipe.camera.capture_array("main")
        brightness_sd = float(frame.std())
        METRICS["camera"] = {"shape": list(frame.shape), "brightness_sd": round(brightness_sd, 1)}
        if frame.shape[:2] != (720, 1280):
            problems.append(f"camera frame is {frame.shape[1]}x{frame.shape[0]}, expected 1280x720")
        elif brightness_sd < 5:
            problems.append(f"camera image is blank (brightness SD {brightness_sd:.1f}): lens covered or sensor fault")

        lcd = None
        try:
            lcd = d.setup_lcd(True)
            d.lcd_text(lcd, "SEARCHING...", "INTEGRATION TEST")
        except OSError as e:
            lcd = None
            problems.append(f"LCD did not answer on I2C ({e}): check SDA/SCL, power, and ground")

        print("  Hold up any sign card in front of the camera (20 s)...")
        frames, streak, last, confirmed = 0, 0, None, None
        start = time.monotonic()
        while time.monotonic() - start < 20 and confirmed is None:
            result = pipe.step()
            frames += 1
            label = result[0] if result else None
            streak = streak + 1 if label is not None and label == last else (1 if label else 0)
            last = label
            if streak >= 3:  # same rule as the demo's --confirm-frames default
                confirmed = result
        elapsed = time.monotonic() - start
    finally:
        pipe.close()

    fps = frames / elapsed
    METRICS["pipeline_fps"] = round(fps, 2)
    if pipe.inference_s:
        METRICS["inference_ms_mean"] = ms(sum(pipe.inference_s) / len(pipe.inference_s))
        METRICS["inference_ms_max"] = ms(max(pipe.inference_s))
    print(f"  {frames} frames in {elapsed:.1f}s -> {fps:.1f} fps; "
          f"model {METRICS.get('inference_ms_mean', '-')} ms per crop")

    if confirmed is None:
        problems.append("no sign confirmed in 20 s")
    else:
        label, confidence = confirmed
        METRICS["pipeline_sign"] = {"read": label, "confidence": round(confidence, 3)}
        print(f"  Read {label} at {confidence:.0%}")
        if lcd is not None:
            try:
                lcd.setRGB(*d.LCD_COLORS[d.SIGN_SHAPES[label][0]])
                d.lcd_text(lcd, label, f"Confidence {confidence:.0%}")
            except OSError as e:
                problems.append(f"LCD stopped answering mid-test ({e})")

    if problems:
        return FAIL, "; ".join(problems)
    return PASS, f"camera OK, LCD acknowledged, read {label} at {confidence:.0%}; {fps:.1f} fps"


TESTS = {
    "pins": test_pins,
    "i2c": test_i2c,
    "line": test_line,
    "imu": test_imu,
    "motors": test_motors,
    "pipeline": test_pipeline,
}


# --------------------------------------------------------------------- Main --
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


def save_report(args, results, metrics=METRICS, prefix="components"):
    """Write <prefix>_<timestamp>.json to --report-dir (stress_test.py uses prefix "stress")."""
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.report_dir / f"{prefix}_{stamp}.json"
    report = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "board": args.board,
        "max_speed_pct": args.max,
        "results": {name: {"status": s, "detail": d} for name, (s, d) in results.items()},
        "metrics": metrics,
    }
    path.write_text(json.dumps(report, indent=2))
    return path


def main():
    p = argparse.ArgumentParser(description="Per-component test for BuggyBot before PCB sign-off.")
    p.add_argument("--only", nargs="+", choices=TESTS, help="run just these stages")
    p.add_argument("--skip", nargs="+", choices=TESTS, default=[], help="skip these stages")
    p.add_argument("--no-motion", action="store_true", help="IMU: skip the interactive motion test")
    p.add_argument("--board", choices=["waveshare", "cokoino"], default="cokoino",
                   help="motor HAT: cokoino (4WD, default) or waveshare (2WD)")
    p.add_argument("--motors", type=int, nargs="+", help="motor numbers to test (default: 1 2)")
    p.add_argument("--max", type=int, default=60, help="motors: max speed %% (default 60)")
    p.add_argument("--report-dir", type=Path, default=HERE.parent / "integration_reports",
                   help="where the JSON report is saved")
    args = p.parse_args()

    names = [n for n in (args.only or TESTS) if n not in args.skip]
    results = {name: run(name, args) for name in names}

    banner("SUMMARY")
    for name, (status, detail) in results.items():
        print(f"  [{status}] {name:<9} {detail}")
    print(f"\n  Report saved to {save_report(args, results)}")
    sys.exit(1 if any(s == FAIL for s, _ in results.values()) else 0)


if __name__ == "__main__":
    main()
