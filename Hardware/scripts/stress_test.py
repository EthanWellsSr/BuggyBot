#!/usr/bin/env python3
"""
stress_test.py - BuggyBot stress test, run before the custom PCB is sent off

The question this answers: does everything work AT THE SAME TIME, on the pins and
buses the PCB will use? Problems that only appear when devices run together
(power dips when motors start, I2C errors from motor noise, two devices on one
pin) are the ones that force a board revision.

Run test_components.py first: it checks each device on its own, so a failure
here can be blamed on running together rather than on a dead part.

The run:

  baseline  the camera + model alone for a few seconds, for the frame rate
            to compare against
  stress    motors reversing, camera + model, IMU, line sensors, and LCD all
            at once, then checks power, I2C errors, line-sensor noise, and
            frame rate

Every run saves a JSON report to Hardware/integration_reports/ (stress_*.json).

Uses the same libraries as test_components.py; run with the LiteRT venv:

  ~/buggybot-venv/bin/python stress_test.py
  ~/buggybot-venv/bin/python stress_test.py --seconds 300
  ~/buggybot-venv/bin/python stress_test.py --board waveshare --max 40

SAFETY: this spins the motors. Lift the wheels off the ground first. Run on
the power source the robot will drive on (the HAT's 7-12 V input): this is a
power test.
"""

import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path

from test_components import (FAIL, HERE, PASS, SKIP, SignPipeline, banner, load_script,
                             open_motors, save_report)

# Measurements collected by the run; written into the JSON report.
METRICS = {}


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


def lcd_worker(d, lcd, stop, c, sign):
    # Writing the LCD keeps the shared I2C bus busy alongside the IMU (and the
    # motor HAT on I2C boards). A sign confirmed by the camera loop is flashed
    # until sign["until"], then the stress counter returns. Only this thread
    # writes the LCD, so camera and counter writes never interleave.
    n = 0
    while not stop.is_set():
        try:
            if time.monotonic() < sign["until"]:
                label, confidence = sign["label"], sign["confidence"]
                lcd.setRGB(*d.LCD_COLORS[d.SIGN_SHAPES[label][0]])
                d.lcd_text(lcd, label, f"Confidence {confidence:.0%}")
            else:
                lcd.setRGB(*d.SEARCHING_COLOR)
                d.lcd_text(lcd, "STRESS TEST", f"update {n}")
            c.add("lcd_writes")
        except Exception as e:
            c.error("lcd", e)
        n += 1
        stop.wait(0.5)


def baseline_fps(pipe, seconds):
    """Frame rate of the camera + model with nothing else running."""
    frames, start = 0, time.monotonic()
    while time.monotonic() - start < seconds:
        pipe.step()
        frames += 1
    return frames / (time.monotonic() - start)


def test_stress(args):
    print("  Runs motors, camera + model, IMU, line sensors, and LCD together for "
          f"{args.seconds:g}s.")
    input("  Lift the wheels, use battery power, keep the line sensors clear, then press Enter...")
    before, temp_before = throttled(), cpu_temp()
    c, stop = Counter(), threading.Event()
    workers, cleanup = [], []
    try:
        pipe = SignPipeline()
        cleanup.append(pipe.close)
        print(f"  Measuring the camera's frame rate alone ({args.baseline_seconds:g}s)...")
        baseline = baseline_fps(pipe, args.baseline_seconds)
        METRICS["baseline_fps"] = round(baseline, 2)
        print(f"  Baseline {baseline:.1f} fps")

        _, hw, motors = open_motors(args)
        cleanup.append(lambda: (hw.all_off(), hw.close()))
        workers.append(threading.Thread(target=motor_worker,
                                        args=(list(motors.values()), max(1, min(100, args.max)), stop, c)))
        icm = load_script("icm20948_test.py").connect()
        workers.append(threading.Thread(target=imu_worker, args=(icm, stop, c)))
        sensors = load_script("Line Sensors.py").LaneSensors()
        cleanup.append(sensors.cleanup)
        workers.append(threading.Thread(target=line_worker, args=(sensors, stop, c)))
        lcd = pipe.d.setup_lcd(True)
        sign = {"label": None, "confidence": 0.0, "until": 0.0}
        workers.append(threading.Thread(target=lcd_worker, args=(pipe.d, lcd, stop, c, sign)))

        for w in workers:
            w.start()
        # The camera pipeline runs here in the main thread, as it does in the demo.
        frames, start = 0, time.monotonic()
        streak, last = 0, None
        while time.monotonic() - start < args.seconds:
            try:
                result = pipe.step()
                frames += 1
                label = result[0] if result else None
                streak = streak + 1 if label is not None and label == last else (1 if label else 0)
                last = label
                # Same 3-frame confirmation as the demo; flash the sign for 2 s.
                if streak == 3 and time.monotonic() >= sign["until"]:
                    sign.update(label=label, confidence=result[1], until=time.monotonic() + 2.0)
                    c.add("signs_shown")
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
    if fps < 0.5 * baseline:
        problems.append(f"camera dropped to {fps:.1f} fps from {baseline:.1f} fps without load")

    if problems:
        return FAIL, "; ".join(problems)
    return PASS, f"{elapsed:.0f}s with no errors, no under-voltage, {fps:.1f} fps"


def main():
    p = argparse.ArgumentParser(description="Stress test for BuggyBot before PCB sign-off.")
    p.add_argument("--board", choices=["waveshare", "cokoino"], default="cokoino",
                   help="motor HAT: cokoino (4WD, default) or waveshare (2WD)")
    p.add_argument("--motors", type=int, nargs="+", help="motor numbers to run (default: 1 2)")
    p.add_argument("--max", type=int, default=60, help="motor speed %% (default 60)")
    p.add_argument("--seconds", type=float, default=120, help="stress run length (default 120)")
    p.add_argument("--baseline-seconds", type=float, default=5,
                   help="camera-only run before the stress run, for the frame-rate baseline (default 5)")
    p.add_argument("--report-dir", type=Path, default=HERE.parent / "integration_reports",
                   help="where the JSON report is saved")
    args = p.parse_args()

    banner("STRESS")
    try:
        status, detail = test_stress(args)
    except (ImportError, SystemExit) as e:
        # SystemExit comes from the individual scripts' own missing-library / no-device exits.
        reason = e.code if isinstance(e, SystemExit) else e
        status, detail = SKIP, f"missing library or device: {reason}"
    except KeyboardInterrupt:
        status, detail = SKIP, "interrupted"
    except Exception as e:
        status, detail = FAIL, f"{type(e).__name__}: {e}"

    banner("SUMMARY")
    print(f"  [{status}] stress    {detail}")
    print(f"\n  Report saved to {save_report(args, {'stress': (status, detail)}, METRICS, 'stress')}")
    sys.exit(1 if status == FAIL else 0)


if __name__ == "__main__":
    main()
