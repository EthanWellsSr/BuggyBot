#!/usr/bin/env python3
"""
test_all_sensors.py - BuggyBot integration test, run before the custom PCB is sent off

The question this answers: does everything work AT THE SAME TIME, on the pins and
buses the PCB will use? Problems that only appear when devices run together
(power dips when motors start, I2C errors from motor noise, two devices on one
pin) are the ones that force a board revision.

Stages, in order (a failure never stops later stages):

  pins      PIN_MAP has no GPIO used by two devices        (no hardware needed)
  i2c       every expected I2C device answers               I2C bus 1
  line      TCRT5000 x2 toggle when a line passes under    GPIO20 left, GPIO21 right
  imu       ICM-20948 still / motion / read-rate checks     I2C 0x69 or 0x68
  motors    each motor spins both ways, brakes, coasts      HAT chosen with --board
  pipeline  camera -> OpenCV -> model -> LCD reads one card Camera Module 3, LCD1602
  stress    everything above running at once, then checks power, I2C errors,
            line-sensor noise, and frame rate

Every run saves a JSON report (results + measurements) to ~/buggybot_integration_reports/
so the team has a record when approving the PCB.

Setup is the union of the individual scripts plus the sign demo's: gpiozero,
adafruit-circuitpython-icm20x, smbus2, picamera2, OpenCV, and LiteRT. Run the
pipeline and stress stages with the LiteRT venv:

  ~/buggybot-venv/bin/python test_all_sensors.py                  # everything
  ~/buggybot-venv/bin/python test_all_sensors.py --only pins i2c  # quick wiring check
  ~/buggybot-venv/bin/python test_all_sensors.py --sign stop --stress-seconds 300
  ~/buggybot-venv/bin/python test_all_sensors.py --board waveshare --max 40

SAFETY: the motors and stress stages spin the motors. Lift the wheels off the
ground first. Run on battery power: the stress stage is a power test.

NOTE: the line sensors moved from GPIO17/27 to GPIO20/21 (10/27) so they no
longer share pins with the Cokoino HAT's motor 1 outputs (GPIO17/27). The
`pins` stage exists so that kind of clash is caught before the PCB is built.
"""

import argparse
import datetime
import importlib.util
import json
import subprocess
import sys
import threading
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
I2C_PINS = {"i2c SDA": 2, "i2c SCL": 3}
LINE_PINS = {"line left": 20, "line right": 21}

# I2C addresses that must answer on bus 1. The LCD is checked by the pipeline
# stage instead, because its addresses depend on the LCD board revision; the
# scan prints every address it finds so they can be written down here.
IMU_ADDRESSES = (0x69, 0x68)


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


def throttled():
    """Raspberry Pi firmware power/thermal flags (vcgencmd get_throttled), or None.

    Low bits are 'happening now'; bits 16+ are 'has happened since boot'.
    0x1/0x10000 under-voltage, 0x2/0x20000 frequency capped,
    0x4/0x40000 throttled, 0x8/0x80000 soft temperature limit.
    """
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=5)
        return int(out.stdout.strip().split("=")[1], 16)
    except Exception:
        return None


def cpu_temp():
    try:
        out = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=5)
        return float(out.stdout.strip().split("=")[1].rstrip("'C"))
    except Exception:
        return None


def describe_throttled(flags):
    names = {0x1: "under-voltage", 0x2: "frequency capped", 0x4: "throttled", 0x8: "soft temp limit"}
    now = [n for bit, n in names.items() if flags & bit]
    since = [n for bit, n in names.items() if flags & (bit << 16)]
    return f"now: {', '.join(now) or 'none'} | since boot: {', '.join(since) or 'none'}"


# --------------------------------------------------------------------- Pins --
def test_pins(args):
    board = load_script("2WDmotor_hat_test.py").BOARDS[args.board]
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
    mod = load_script("2WDmotor_hat_test.py")
    board = mod.BOARDS[args.board]
    found = mod.scan_bus(1)
    METRICS["i2c_addresses"] = [f"0x{a:02X}" for a in found]
    missing = []
    if not any(a in found for a in IMU_ADDRESSES):
        missing.append("IMU (0x69/0x68)")
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
    mod = load_script("2WDmotor_hat_test.py")
    board = mod.BOARDS[args.board]
    nums = args.motors or sorted(board["motors"])
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
    sign = args.sign or input("  Which sign card will you hold up (e.g. stop, merge)? ").strip()
    pipe = SignPipeline()
    d = pipe.d
    if sign not in pipe.labels:
        pipe.close()
        return FAIL, f"unknown sign '{sign}'; choose from {', '.join(pipe.labels)}"
    lcd = d.setup_lcd(True)
    d.lcd_text(lcd, "SEARCHING...", "INTEGRATION TEST")
    input(f"  Hold the {sign} card in front of the camera, then press Enter...")
    frames, streak, last, confirmed = 0, 0, None, None
    start = time.monotonic()
    try:
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
        d.lcd_text(lcd, "NO SIGN FOUND", "")
        return FAIL, f"no sign confirmed in 20 s (expected {sign})"
    label, confidence = confirmed
    lcd.setRGB(*d.LCD_COLORS[d.SIGN_SHAPES[label][0]])
    d.lcd_text(lcd, label, f"Confidence {confidence:.0%}")
    METRICS["pipeline_sign"] = {"expected": sign, "read": label, "confidence": round(confidence, 3)}
    if label != sign:
        return FAIL, f"read {label} instead of {sign}"
    color = d.SIGN_SHAPES[label][0]
    ans = input(f"  Does the LCD show '{label}' with a {color} backlight? [y/n] ").strip().lower()
    lcd.setRGB(*d.SEARCHING_COLOR)
    d.lcd_text(lcd, "BUGGYBOT", "PIPELINE OK" if ans == "y" else "PIPELINE FAIL")
    if ans != "y":
        return FAIL, "LCD did not show the sign correctly: check I2C wiring and LCD power"
    return PASS, f"read {label} at {confidence:.0%}; {fps:.1f} fps"


# ------------------------------------------------------------------- Stress --
class Counter:
    """Thread-safe tallies shared between the stress workers."""

    def __init__(self):
        self.lock = threading.Lock()
        self.counts = {}
        self.errors = []

    def add(self, key, n=1):
        with self.lock:
            self.counts[key] = self.counts.get(key, 0) + n

    def error(self, where, exc):
        with self.lock:
            self.counts[f"{where}_errors"] = self.counts.get(f"{where}_errors", 0) + 1
            if len(self.errors) < 20:
                self.errors.append(f"{where}: {type(exc).__name__}: {exc}")


def motor_worker(motors, speed, stop, c):
    # Repeated direction changes at full test speed draw the largest current
    # spikes, which is what exposes weak power wiring.
    direction = 1
    while not stop.is_set():
        try:
            for m in motors:
                m.run(direction * speed)
            c.add("motor_reversals")
        except Exception as e:
            c.error("motor", e)
        direction = -direction
        stop.wait(1.0)
    for m in motors:
        m.coast()


def imu_worker(icm, stop, c):
    # The chassis is lifted and still, so gravity should read ~9.8 m/s^2 even
    # with the motors vibrating. Readings far from that point to corrupted I2C data.
    while not stop.is_set():
        try:
            ax, ay, az = icm.acceleration
            icm.gyro
            c.add("imu_reads")
            g = (ax * ax + ay * ay + az * az) ** 0.5
            if not 5.0 < g < 15.0:
                c.add("imu_implausible")
        except Exception as e:
            c.error("imu", e)
        time.sleep(0.01)


def line_worker(sensors, stop, c):
    # Nothing passes under the sensors during the stress run, so any change in
    # their output is electrical noise (often from the motors).
    last = (sensors.left_sensor.value, sensors.right_sensor.value)
    while not stop.is_set():
        try:
            now = (sensors.left_sensor.value, sensors.right_sensor.value)
            c.add("line_reads")
            if now != last:
                c.add("line_toggles")
            last = now
        except Exception as e:
            c.error("line", e)
        time.sleep(0.005)


def lcd_worker(d, lcd, stop, c):
    # Writing the LCD keeps the shared I2C bus busy alongside the IMU (and the
    # motor HAT on I2C boards).
    n = 0
    while not stop.is_set():
        try:
            d.lcd_text(lcd, "STRESS TEST", f"update {n}")
            c.add("lcd_writes")
        except Exception as e:
            c.error("lcd", e)
        n += 1
        stop.wait(0.5)


def test_stress(args):
    print("  Runs motors, camera + model, IMU, line sensors, and LCD together for "
          f"{args.stress_seconds:g}s.")
    input("  Lift the wheels, use battery power, keep the line sensors clear, then press Enter...")
    before, temp_before = throttled(), cpu_temp()
    c, stop = Counter(), threading.Event()
    workers, cleanup = [], []
    try:
        _, hw, motors = open_motors(args)
        cleanup.append(lambda: (hw.all_off(), hw.close()))
        workers.append(threading.Thread(target=motor_worker,
                                        args=(list(motors.values()), max(1, min(100, args.max)), stop, c)))
        icm = load_script("icm20948_test.py").connect()
        workers.append(threading.Thread(target=imu_worker, args=(icm, stop, c)))
        sensors = load_script("Line Sensors.py").LaneSensors()
        cleanup.append(sensors.cleanup)
        workers.append(threading.Thread(target=line_worker, args=(sensors, stop, c)))
        pipe = SignPipeline()
        cleanup.append(pipe.close)
        lcd = pipe.d.setup_lcd(True)
        workers.append(threading.Thread(target=lcd_worker, args=(pipe.d, lcd, stop, c)))

        for w in workers:
            w.start()
        # The camera pipeline runs here in the main thread, as it does in the demo.
        frames, start = 0, time.monotonic()
        while time.monotonic() - start < args.stress_seconds:
            try:
                pipe.step()
                frames += 1
            except Exception as e:
                c.error("camera", e)
            elapsed = time.monotonic() - start
            print(f"\r  {elapsed:5.0f}s  frames {frames}  imu {c.counts.get('imu_reads', 0)}  "
                  f"errors {sum(v for k, v in c.counts.items() if k.endswith('_errors'))}   ",
                  end="", flush=True)
        print()
        elapsed = time.monotonic() - start
    finally:
        stop.set()
        for w in workers:
            w.join(timeout=5)
        for fn in reversed(cleanup):
            try:
                fn()
            except Exception:
                pass
        print("  All motors stopped.")

    after, temp_after = throttled(), cpu_temp()
    fps = frames / elapsed
    METRICS["stress"] = {
        "seconds": round(elapsed, 1),
        "fps": round(fps, 2),
        "counts": c.counts,
        "first_errors": c.errors,
        "throttled_before": None if before is None else hex(before),
        "throttled_after": None if after is None else hex(after),
        "cpu_temp_before_c": temp_before,
        "cpu_temp_after_c": temp_after,
    }
    for line in c.errors:
        print(f"  ! {line}")
    print(f"  Camera {fps:.1f} fps | counts {c.counts}")
    print(f"  CPU {temp_before} -> {temp_after} C")

    problems = []
    if before is None or after is None:
        problems.append("could not read vcgencmd get_throttled (power not checked)")
    else:
        print(f"  Power/thermal {describe_throttled(after)}")
        new = after & ~before
        if after & 0x1 or new & 0x10000:
            problems.append("under-voltage during the run: check battery, regulator, and power traces")
        if after & 0xE or new & 0xE0000:
            problems.append("CPU throttled or capped during the run (heat or power)")
    for where in ("imu", "lcd", "line", "motor", "camera"):
        if c.counts.get(f"{where}_errors"):
            problems.append(f"{c.counts[f'{where}_errors']} {where} errors")
    if c.counts.get("imu_implausible"):
        problems.append(f"{c.counts['imu_implausible']} implausible IMU readings (I2C noise?)")
    if c.counts.get("line_toggles"):
        problems.append(f"line sensors toggled {c.counts['line_toggles']} times with nothing under "
                        "them (motor noise on GPIO20/21?)")
    baseline = METRICS.get("pipeline_fps")
    if baseline and fps < 0.5 * baseline:
        problems.append(f"camera dropped to {fps:.1f} fps from {baseline:.1f} fps without load")

    if problems:
        return FAIL, "; ".join(problems)
    return PASS, f"{elapsed:.0f}s with no errors, no under-voltage, {fps:.1f} fps"


TESTS = {
    "pins": test_pins,
    "i2c": test_i2c,
    "line": test_line,
    "imu": test_imu,
    "motors": test_motors,
    "pipeline": test_pipeline,
    "stress": test_stress,
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


def save_report(args, results):
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.report_dir / f"integration_{stamp}.json"
    report = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "board": args.board,
        "max_speed_pct": args.max,
        "results": {name: {"status": s, "detail": d} for name, (s, d) in results.items()},
        "metrics": METRICS,
    }
    path.write_text(json.dumps(report, indent=2))
    return path


def main():
    p = argparse.ArgumentParser(description="Integration test for BuggyBot before PCB sign-off.")
    p.add_argument("--only", nargs="+", choices=TESTS, help="run just these stages")
    p.add_argument("--skip", nargs="+", choices=TESTS, default=[], help="skip these stages")
    p.add_argument("--no-motion", action="store_true", help="IMU: skip the interactive motion test")
    p.add_argument("--board", choices=["cokoino", "waveshare", "adafruit"], default="cokoino",
                   help="motor HAT to test (default cokoino)")
    p.add_argument("--motors", type=int, nargs="+", help="motor numbers to test (default: all)")
    p.add_argument("--max", type=int, default=60, help="motors: max speed %% (default 60)")
    p.add_argument("--sign", help="pipeline: the sign card you will hold up (asked if omitted)")
    p.add_argument("--stress-seconds", type=float, default=120, help="stress: run length (default 120)")
    p.add_argument("--report-dir", type=Path, default=Path.home() / "buggybot_integration_reports",
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
