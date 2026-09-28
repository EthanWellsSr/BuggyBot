#!/usr/bin/env python3
"""
motor_hat_test.py - bench test for PCA9685 + TB6612 motor controller HATs

Supported boards (pick with --board):
  adafruit   Adafruit DC & Stepper Motor HAT   (I2C 0x60, motors M1-M4)
  waveshare  Waveshare Motor Driver HAT        (I2C 0x40, motors A/B -> 1/2)

Talks to the PCA9685 directly over I2C, so the only dependency is smbus2.

Setup (Raspberry Pi):
  sudo raspi-config  -> Interface Options -> I2C -> Enable, then reboot
  pip install smbus2
  i2cdetect -y 1     (optional: confirm the HAT shows up at 0x60 or 0x40)

Usage:
  python3 motor_hat_test.py --board adafruit             # full automatic test
  python3 motor_hat_test.py --board waveshare --max 40   # gentler test
  python3 motor_hat_test.py --board adafruit --motors 1 2
  python3 motor_hat_test.py --board adafruit -i          # interactive control
  python3 motor_hat_test.py --scan                       # just scan the I2C bus

SAFETY: lift the wheels off the ground before running. Ctrl+C stops all motors.
"""

import argparse
import signal
import sys
import time

try:
    from smbus2 import SMBus
except ImportError:
    sys.exit("smbus2 is not installed. Run: pip install smbus2  (and enable I2C in raspi-config)")


# Channel map per board: motor number -> (PWM channel, IN1 channel, IN2 channel)
BOARDS = {
    "adafruit": {
        "name": "Adafruit DC & Stepper Motor HAT",
        "addr": 0x60,
        "freq": 1600,
        "motors": {1: (8, 10, 9), 2: (13, 11, 12), 3: (2, 4, 3), 4: (7, 5, 6)},
    },
    "waveshare": {
        "name": "Waveshare Motor Driver HAT",
        "addr": 0x40,
        "freq": 1000,
        "motors": {1: (0, 1, 2), 2: (5, 3, 4)},
    },
}


# ---------------------------------------------------------------- PCA9685 ----
class PCA9685:
    MODE1 = 0x00
    MODE2 = 0x01
    LED0_ON_L = 0x06
    ALL_LED_ON_L = 0xFA
    PRESCALE = 0xFE
    OSC_HZ = 25_000_000

    def __init__(self, bus, addr, freq):
        self.bus = bus
        self.addr = addr
        self.bus.write_byte_data(addr, self.MODE1, 0x20)  # awake, register auto-increment
        self.bus.write_byte_data(addr, self.MODE2, 0x04)  # totem-pole outputs
        time.sleep(0.005)
        self.all_off()
        self.set_freq(freq)

    def set_freq(self, freq):
        prescale = round(self.OSC_HZ / (4096 * freq)) - 1
        prescale = max(3, min(255, prescale))            # hardware limits (~24 Hz - ~1526 Hz)
        old = self.bus.read_byte_data(self.addr, self.MODE1)
        self.bus.write_byte_data(self.addr, self.MODE1, (old & 0x7F) | 0x10)  # sleep to change prescale
        self.bus.write_byte_data(self.addr, self.PRESCALE, prescale)
        self.bus.write_byte_data(self.addr, self.MODE1, old & 0x7F)
        time.sleep(0.005)
        self.bus.write_byte_data(self.addr, self.MODE1, (old & 0x7F) | 0x80)  # restart
        self.freq = self.OSC_HZ / (4096 * (prescale + 1))

    def _set(self, ch, on, off):
        reg = self.LED0_ON_L + 4 * ch
        self.bus.write_i2c_block_data(self.addr, reg, [on & 0xFF, on >> 8, off & 0xFF, off >> 8])

    def duty(self, ch, value):
        """value 0.0 - 1.0"""
        if value <= 0:
            self._set(ch, 0, 0x1000)          # full off
        elif value >= 1:
            self._set(ch, 0x1000, 0)          # full on
        else:
            self._set(ch, 0, int(value * 4095))

    def pin(self, ch, high):
        self.duty(ch, 1.0 if high else 0.0)

    def all_off(self):
        self.bus.write_i2c_block_data(self.addr, self.ALL_LED_ON_L, [0, 0, 0, 0x10])


# ------------------------------------------------------------------ Motor ----
class Motor:
    def __init__(self, pca, number, pwm_ch, in1_ch, in2_ch, invert=False):
        self.pca = pca
        self.number = number
        self.pwm, self.in1, self.in2 = pwm_ch, in1_ch, in2_ch
        self.invert = invert

    def run(self, speed):
        """speed -100..100 (percent). 0 = coast."""
        speed = max(-100.0, min(100.0, float(speed)))
        if self.invert:
            speed = -speed
        if speed > 0:
            self.pca.pin(self.in2, False)
            self.pca.pin(self.in1, True)
        elif speed < 0:
            self.pca.pin(self.in1, False)
            self.pca.pin(self.in2, True)
        else:
            self.pca.pin(self.in1, False)
            self.pca.pin(self.in2, False)
        self.pca.duty(self.pwm, abs(speed) / 100.0)

    def brake(self):
        """TB6612 short brake: both inputs high."""
        self.pca.pin(self.in1, True)
        self.pca.pin(self.in2, True)
        self.pca.duty(self.pwm, 1.0)

    def coast(self):
        self.run(0)


# ------------------------------------------------------------------ Tests ----
def ramp(motor, target, step, dwell):
    """Ramp from 0 to target (signed), then back to 0."""
    sign = 1 if target >= 0 else -1
    levels = list(range(0, abs(target) + 1, step))
    if levels[-1] != abs(target):
        levels.append(abs(target))
    for lvl in levels + levels[-2::-1]:
        motor.run(sign * lvl)
        print(f"\r  M{motor.number}: {sign * lvl:+4d}%   ", end="", flush=True)
        time.sleep(dwell)
    motor.coast()
    print()


def test_motor(motor, max_speed, step, dwell, hold):
    n = motor.number
    print(f"\n=== Motor {n} ===")

    print("  Forward ramp")
    ramp(motor, max_speed, step, dwell)
    time.sleep(0.5)

    print("  Reverse ramp")
    ramp(motor, -max_speed, step, dwell)
    time.sleep(0.5)

    print(f"  Hold {max_speed}% forward for {hold}s, then BRAKE")
    motor.run(max_speed)
    time.sleep(hold)
    motor.brake()
    time.sleep(0.5)
    motor.coast()

    print(f"  Hold {max_speed}% forward for {hold}s, then COAST (should spin down slower than brake)")
    motor.run(max_speed)
    time.sleep(hold)
    motor.coast()
    time.sleep(1.0)

    ans = input(f"  Did motor {n} spin both ways and brake harder than it coasted? [y/n/skip] ").strip().lower()
    return {"y": "PASS", "n": "FAIL"}.get(ans, "SKIPPED")


def test_all_together(motors, speed, hold):
    print(f"\n=== All motors together at {speed}% ===")
    for m in motors:
        m.run(speed)
    time.sleep(hold)
    for m in motors:
        m.run(-speed)
    time.sleep(hold)
    for m in motors:
        m.coast()
    ans = input("  Did all motors run together in both directions? [y/n/skip] ").strip().lower()
    return {"y": "PASS", "n": "FAIL"}.get(ans, "SKIPPED")


def interactive(motors_by_num, max_speed):
    help_text = f"""
Commands:
  <motor> <speed>   run a motor, speed -{max_speed}..{max_speed}   e.g.  1 50   2 -30
  all <speed>       run all motors                        e.g.  all 40
  b <motor|all>     brake
  s                 stop (coast) all motors
  r <motor>         run the ramp test on one motor
  h                 show this help
  q                 quit
"""
    print(help_text)
    while True:
        try:
            parts = input("motor> ").strip().lower().split()
        except EOFError:
            break
        if not parts:
            continue
        cmd = parts[0]
        try:
            if cmd == "q":
                break
            elif cmd == "h":
                print(help_text)
            elif cmd == "s":
                for m in motors_by_num.values():
                    m.coast()
            elif cmd == "b":
                targets = motors_by_num.values() if parts[1] == "all" else [motors_by_num[int(parts[1])]]
                for m in targets:
                    m.brake()
            elif cmd == "r":
                ramp(motors_by_num[int(parts[1])], max_speed, 10, 0.15)
            else:
                speed = max(-max_speed, min(max_speed, float(parts[1])))
                targets = motors_by_num.values() if cmd == "all" else [motors_by_num[int(cmd)]]
                for m in targets:
                    m.run(speed)
                print(f"  -> {speed:+.0f}%")
        except (IndexError, ValueError, KeyError):
            print("  Didn't understand that. Type h for help.")


def scan_bus(bus_num):
    print(f"Scanning I2C bus {bus_num}...")
    found = []
    with SMBus(bus_num) as bus:
        for addr in range(0x03, 0x78):
            try:
                bus.read_byte(addr)
                found.append(addr)
            except OSError:
                pass
    if found:
        print("  Devices found at: " + ", ".join(f"0x{a:02X}" for a in found))
        print("  (0x70 is the PCA9685 all-call address and is normal to see.)")
    else:
        print("  No devices found. Check that I2C is enabled and the HAT is seated.")
    return found


# ------------------------------------------------------------------- Main ----
def main():
    p = argparse.ArgumentParser(description="Test a PCA9685/TB6612 motor controller HAT.")
    p.add_argument("--board", choices=BOARDS.keys(), default="adafruit")
    p.add_argument("--addr", type=lambda x: int(x, 0), help="override I2C address, e.g. 0x61")
    p.add_argument("--bus", type=int, default=1, help="I2C bus number (default 1)")
    p.add_argument("--freq", type=float, help="PWM frequency in Hz (default depends on board)")
    p.add_argument("--motors", type=int, nargs="+", help="which motors to test (default: all)")
    p.add_argument("--invert", type=int, nargs="+", default=[], help="motors whose direction to flip")
    p.add_argument("--max", type=int, default=60, help="max speed %% used in tests (default 60)")
    p.add_argument("--step", type=int, default=10, help="ramp step %% (default 10)")
    p.add_argument("--dwell", type=float, default=0.2, help="seconds per ramp step")
    p.add_argument("--hold", type=float, default=1.5, help="seconds to hold speed in brake/coast tests")
    p.add_argument("-i", "--interactive", action="store_true", help="manual control mode")
    p.add_argument("--scan", action="store_true", help="scan the I2C bus and exit")
    args = p.parse_args()

    if args.scan:
        scan_bus(args.bus)
        return

    board = BOARDS[args.board]
    addr = args.addr if args.addr is not None else board["addr"]
    freq = args.freq or board["freq"]
    max_speed = max(1, min(100, args.max))

    print(f"Board: {board['name']}  |  I2C bus {args.bus}, address 0x{addr:02X}")

    try:
        bus = SMBus(args.bus)
    except (FileNotFoundError, PermissionError) as e:
        sys.exit(f"Can't open I2C bus {args.bus}: {e}\nEnable I2C in raspi-config and make sure your user is in the i2c group.")

    try:
        bus.read_byte_data(addr, PCA9685.MODE1)
    except OSError:
        print(f"No response at 0x{addr:02X}.")
        scan_bus(args.bus)
        sys.exit("Fix the address with --addr, or check wiring/power, then try again.")

    pca = PCA9685(bus, addr, freq)
    print(f"PCA9685 OK. PWM frequency set to {pca.freq:.0f} Hz")

    nums = args.motors or sorted(board["motors"])
    bad = [n for n in nums if n not in board["motors"]]
    if bad:
        sys.exit(f"{board['name']} has motors {sorted(board['motors'])}; got {bad}")
    motors = {n: Motor(pca, n, *board["motors"][n], invert=n in args.invert) for n in nums}

    def shutdown(*_):
        pca.all_off()
        bus.close()
        print("\nAll motors stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        if args.interactive:
            interactive(motors, max_speed)
        else:
            input("\nLift the wheels off the ground, check motor power is on, then press Enter to start...")
            results = {}
            for n, m in motors.items():
                results[f"Motor {n}"] = test_motor(m, max_speed, args.step, args.dwell, args.hold)
            if len(motors) > 1:
                results["All together"] = test_all_together(list(motors.values()), max_speed, args.hold)

            print("\n=== Summary ===")
            for name, r in results.items():
                print(f"  {name:<14} {r}")
            if "FAIL" in results.values():
                print("\nTips for a FAIL: check motor supply voltage at the HAT's power terminal, "
                      "screw terminals, and that the motor spins when wired straight to a battery.")
    finally:
        pca.all_off()
        bus.close()
        print("All motors stopped.")


if __name__ == "__main__":
    main()
