#On the Raspberry Pi, open a terminal and make sure "GPIO Zero" is installed:
#sudo apt update
#sudo apt install python3-gpiozero
#This can be removed later, just want to confirm it works ^

from gpiozero import DistanceSensor #so Python can control/read US-sensor
from time import sleep #to pause between readings

sensor = DistanceSensor(
    echo=18, #connected to GPIO18 - Physical Pin 12
    trigger=17, #connected to GPIO17 - Physical Pin 11
    max_distance=4 #in meters
)

while True:

    # gpiozero gives distance in meters, so convert to cm
    distance_cm = sensor.distance * 100

    print("Distance:", round(distance_cm, 2), "cm")

    sleep(0.5)