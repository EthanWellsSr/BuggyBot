#!/usr/bin/env python3
"""
motor_hat_test.py - bench test for Raspberry Pi motor controller HATs

Supported boards (pick with --board):
  cokoino    Cokoino 4WD Robot HAT             (GPIO direct, 2x DRV8833, motors M1-M4)
  waveshare  Waveshare Motor Driver HAT        (I2C 0x40, PCA9685 + TB6612, motors A/B -> 1/2)
  adafruit   Adafruit DC & Stepper Motor HAT   (I2C 0x60, PCA9685 + TB6612, motors M1-M4)

Setup (Raspberry Pi OS):
  Cokoino:            sudo apt install python3-gpiozero python3-lgpio   (usually preinstalled)
  Waveshare/Adafruit: sudo raspi-config -> Interface Options -> I2C -> Enable, reboot
                      sudo apt install python3-smbus2 i2c-tools

Usage:
  python3 motor_hat_test.py --board cokoino              # full automatic test
  python3 motor_hat_test.py --board waveshare --max 40   # gentler test
  python3 motor_hat_test.py --board cokoino --motors 1 3
  python3 motor_hat_test.py --board cokoino -i           # interactive control
  python3 motor_hat_test.py --scan                       # scan the I2C bus (I2C boards only)

SAFETY: lift the wheels off the ground before running. Ctrl+C stops all motors.
"""

import argparse
import signal
import sys
import time


# I2C boards: motor number -> (PWM channel, IN1 channel, IN2 channel) on the PCA9685
# GPIO boards: motor number -> (sleep/enable pin, IN1 pin, IN2 pin), BCM numbering
BOARDS = {
    "cokoino": {
        "name": "Cokoino 4WD Robot HAT",
        "type": "gpio",
        "freq": 500,
        # From the vendor schematic: U3 (NSLEEP=GPIO12) drives M1/M2, U2 (NSLEEP=GPIO13) drives M3/M4
        "motors": {1: (12, 17, 27), 2: (12, 22, 23), 3: (13, 24, 25), 4: (13, 26, 16)},
    },
    "waveshare": {
        "name": "Waveshare Motor Driver HAT",
        "type": "i2c",
        "addr": 0x40,
        "freq": 1000,
        "motors": {1: (0, 1, 2), 2: (5, 3, 4)},
    },
    "adafruit": {
        "name": "Adafruit DC & Stepper Motor HAT",
        "type": "i2c",
        "addr": 0x60,
        "freq": 1600,
        "motors": {1: (8, 10, 9), 2: (13, 11, 12), 3: (2, 4, 3), 4: (7, 5, 6)},
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


# ----------------------------------------------------------------- Motors ----
class PCAMotor:
    """TB6612 channel driven through a PCA9685 (Waveshare / Adafruit)."""

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


class GPIOMotor:
    """DRV8833 channel driven straight from Pi GPIO (Cokoino).

    Speed is set by PWM on the IN pins with NSLEEP held high, so every motor
    gets its own speed (the vendor demo PWMs NSLEEP instead, which forces
    M1/M2 and M3/M4 to share one speed).
    """

    def __init__(self, gz_motor, number, invert=False):
        self.m = gz_motor
        self.number = number
        self.invert = invert

    def run(self, speed):
        speed = max(-100.0, min(100.0, float(speed)))
        if self.invert:
            speed = -speed
        if speed > 0:
            self.m.forward(speed / 100.0)
        elif speed < 0:
            self.m.backward(-speed / 100.0)
        else:
            self.m.stop()                      # both IN low = coast

    def brake(self):
        """DRV8833 brake: both inputs high."""
        self.m.forward_device.value = 1
        self.m.backward_device.value = 1

    def coast(self):
        self.m.stop()


# --------------------------------------------------------------- Hardware ----
class I2CHardware:
    def __init__(self, board, args):
        try:
            from smbus2 import SMBus
        except ImportError:
            sys.exit("smbus2 is not installed. Run: sudo apt install python3-smbus2")

        addr = args.addr if args.addr is not None else board["addr"]
        print(f"Board: {board['name']}  |  I2C bus {args.bus}, address 0x{addr:02X}")
        try:
            self.bus = SMBus(args.bus)
        except (FileNotFoundError, PermissionError) as e:
            sys.exit(f"Can't open I2C bus {args.bus}: {e}\n"
                     "Enable I2C in raspi-config and make sure your user is in the i2c group.")
        try:
            self.bus.read_byte_data(addr, PCA9685.MODE1)
        except OSError:
            print(f"No response at 0x{addr:02X}.")
            scan_bus(args.bus)
            sys.exit("Fix the address with --addr, or check wiring/power, then try again.")

        self.pca = PCA9685(self.bus, addr, args.freq or board["freq"])
        print(f"PCA9685 OK. PWM frequency set to {self.pca.freq:.0f} Hz")

    def make_motor(self, n, pins, invert):
        return PCAMotor(self.pca, n, *pins, invert=invert)

    def all_off(self):
        self.pca.all_off()

    def close(self):
        self.bus.close()


class GPIOHardware:
    def __init__(self, board, args):
        try:
            from gpiozero import Motor, DigitalOutputDevice
        except ImportError:
            sys.exit("gpiozero is not installed. Run: sudo apt install python3-gpiozero python3-lgpio")
        self.Motor = Motor
        self.freq = args.freq or board["freq"]
        print(f"Board: {board['name']}  |  GPIO direct, PWM {self.freq:.0f} Hz")

        # Wake both DRV8833 chips (NSLEEP high). Only the pins actually used get claimed.
        self.sleep_pins = {}
        for sleep, _, _ in board["motors"].values():
            if sleep not in self.sleep_pins:
                try:
                    self.sleep_pins[sleep] = DigitalOutputDevice(sleep, initial_value=True)
                except Exception as e:
                    sys.exit(f"Can't claim GPIO{sleep}: {e}\n"
                             "Is another program (or a dtoverlay like pwm/audio) using it?")
        self.motors = []

    def make_motor(self, n, pins, invert):
        _, in1, in2 = pins
        m = self.Motor(forward=in1, backward=in2, pwm=True)
        m.forward_device.frequency = self.freq
        m.backward_device.frequency = self.freq
        m.stop()
        self.motors.append(m)
        return GPIOMotor(m, n, invert=invert)

    def all_off(self):
        for m in self.motors:
            m.stop()
        for p in self.sleep_pins.values():
            p.off()                            # NSLEEP low: outputs high-impedance

    def close(self):
        for m in self.motors:
            m.close()
        for p in self.sleep_pins.values():
            p.close()


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
    try:
        from smbus2 import SMBus
    except ImportError:
        sys.exit("smbus2 is not installed. Run: sudo apt install python3-smbus2")
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
        print("  (The Cokoino HAT has no I2C chip, so it never shows up here.)")
    return found


# ------------------------------------------------------------------- Main ----
def main():
    p = argparse.ArgumentParser(description="Test a Raspberry Pi motor controller HAT.")
    p.add_argument("--board", choices=BOARDS.keys(), default="cokoino")
    p.add_argument("--addr", type=lambda x: int(x, 0), help="I2C boards: override address, e.g. 0x41")
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
    max_speed = max(1, min(100, args.max))

    nums = args.motors or sorted(board["motors"])
    bad = [n for n in nums if n not in board["motors"]]
    if bad:
        sys.exit(f"{board['name']} has motors {sorted(board['motors'])}; got {bad}")

    hw = (GPIOHardware if board["type"] == "gpio" else I2CHardware)(board, args)
    motors = {n: hw.make_motor(n, board["motors"][n], n in args.invert) for n in nums}

    def shutdown(*_):
        hw.all_off()
        hw.close()
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
                print("\nTips for a FAIL: check battery voltage and the HAT's power switch, "
                      "the motor terminals, and that the motor spins when wired straight to a battery.")
    finally:
        hw.all_off()
        hw.close()
        print("All motors stopped.")


if __name__ == "__main__":
    main()
