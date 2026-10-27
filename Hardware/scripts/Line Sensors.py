
"""
Connections:
    Left Sensor DO  -> GPIO20 (Physical Pin 38)
    Right Sensor DO -> GPIO21 (Physical Pin 40)
    Both VCC        -> 3.3V
    Both GND        -> GND
"""

from dataclasses import dataclass
from time import sleep
from gpiozero import DigitalInputDevice

# GPIO CONFIGURATION
LEFT_GPIO = 20
RIGHT_GPIO = 21

# TCRT5000 output trigger
BOUNDARY_ACTIVE_LOW = True

# Delay between sensor readings
POLL_INTERVAL = 0.05


# SENSOR DATA STRUCTURE
@dataclass
class LaneReading:
    left_boundary: bool
    right_boundary: bool
    action: str


# SENSOR CLASS
class LaneSensors:

    def __init__(self):

        # Initialize left and right IR sensors
        self.left_sensor = DigitalInputDevice(
            LEFT_GPIO,
            pull_up=None
        )
        self.right_sensor = DigitalInputDevice(
            RIGHT_GPIO,
            pull_up=None
        )
        print("TCRT5000 Sensors Initialized")

    # READ INDIVIDUAL SENSOR
    def detect_boundary(self, sensor):
        sensor_value = sensor.value

        if BOUNDARY_ACTIVE_LOW:
            return sensor_value == 0
        else:
            return sensor_value == 1

    # READ BOTH SENSORS
    def read_sensors(self):

        left_detected = self.detect_boundary(
            self.left_sensor
        )

        right_detected = self.detect_boundary(
            self.right_sensor
        )

        # Determine navigation correction
        if left_detected and right_detected:
            action = "STOP_CHECK_TRACK"

        elif left_detected:
            action = "CORRECT_RIGHT"

        elif right_detected:
            action = "CORRECT_LEFT"

        else:
            action = "KEEP_FORWARD"

        return LaneReading(
            left_boundary=left_detected,
            right_boundary=right_detected,
            action=action
        )

    # GPIO CLEANUP
    def cleanup(self):
        self.left_sensor.close()
        self.right_sensor.close()
        print("GPIO Sensors Released")

# MAIN PROGRAM
def main():
    print("BuggyBot IR Sensor Monitoring")
    sensors = LaneSensors()
    previous_reading = None
    try:
        while True:
            reading = sensors.read_sensors()

            # Print only when sensor status changes
            if reading != previous_reading:
                print(
                    f"Left Boundary: {reading.left_boundary} | "
                    f"Right Boundary: {reading.right_boundary} | "
                    f"Action: {reading.action}"
                )

                previous_reading = reading

            sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nSensor Monitoring Stopped")

    finally:
        sensors.cleanup()

# PROGRAM ENTRY POINT
if __name__ == "__main__":
    main()
