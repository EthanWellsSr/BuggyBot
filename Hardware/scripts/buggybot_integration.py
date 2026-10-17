import sys
import time
import subprocess
from pathlib import Path

# ==========================================
# 1. WAVESHARE LCD LIBRARY
# ==========================================

# Location of your existing LCD library
LCD_LIBRARY_PATH = (
    "/home/buggybot/"
    "LCD1602-RGB-Module-demo/Raspberry"
)

# Tell Python where to find RGB1602.py
sys.path.insert(0, LCD_LIBRARY_PATH)

import RGB1602


# ==========================================
# 2. CONFIGURATION
# ==========================================

# Choose "manual" or "automatic"
TEST_MODE = "manual"

# Initialize LCD
lcd = RGB1602.RGB1602(16, 2)

# RGB backlight colors
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)

# Folder for captured images
IMAGE_FOLDER = Path(
    "/home/buggybot/buggybot_images"
)

IMAGE_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

# Simulated machine learning predictions
PREDICTIONS = [
    "STOP",
    "LEFT",
    "RIGHT",
    "SLOW",
    "SPEED_LIMIT",
    "NO_ENTRY",
    "GO",
    "NONE"
]


# ==========================================
# 3. LCD DISPLAY FUNCTION
# ==========================================

def display_message(line1, line2, color):

    lcd.clear()

    # Set RGB backlight color
    lcd.setRGB(*color)

    # Display first line
    lcd.setCursor(0, 0)
    lcd.printout(line1[:16])

    # Display second line
    lcd.setCursor(0, 1)
    lcd.printout(line2[:16])


# ==========================================
# 4. CAMERA CAPTURE FUNCTION
# ==========================================

def capture_image(image_number):

    filename = (
        IMAGE_FOLDER
        / f"image_{image_number:04d}.jpg"
    )

    print(
        f"\nCapturing image: {filename}",
        flush=True
    )

    # Capture using your working camera software
    subprocess.run(
        [
            "rpicam-still",
            "-n",
            "-t", "1000",
            "-o", str(filename)
        ],
        check=True
    )

    print(
        f"Image saved: {filename}",
        flush=True
    )

    return filename


# ==========================================
# 5. SIMULATED MACHINE LEARNING MODEL
# ==========================================

def simulated_prediction(
    image_path,
    mode,
    prediction_number
):

    # The actual ML model will eventually
    # replace this function.
    #
    # For now, predictions are simulated.
    # The program does NOT analyze the image.

    if mode == "automatic":

        prediction = PREDICTIONS[
            prediction_number % len(PREDICTIONS)
        ]

    else:

        print(
            f"\nImage captured: {image_path}"
        )

        print("\nSelect a simulated prediction:")

        for number, sign in enumerate(
            PREDICTIONS, 1
        ):
            print(f"{number}. {sign}")

        while True:

            choice = input(
                "\nChoose prediction (1-8): "
            ).strip()

            if choice.isdigit():

                number = int(choice)

                if 1 <= number <= len(PREDICTIONS):

                    prediction = PREDICTIONS[
                        number - 1
                    ]

                    break

            print(
                "Please enter a number from 1 to 8."
            )

    print(
        f"Simulated prediction: {prediction}",
        flush=True
    )

    return prediction


# ==========================================
# 6. DECISION LOGIC
# ==========================================

def process_prediction(prediction):

    if prediction == "STOP":

        return (
            "STOP SIGN",
            "STOP",
            RED
        )

    elif prediction == "LEFT":

        return (
            "LEFT TURN",
            "TURN LEFT",
            YELLOW
        )

    elif prediction == "RIGHT":

        return (
            "RIGHT TURN",
            "TURN RIGHT",
            YELLOW
        )

    elif prediction == "SLOW":

        return (
            "SLOW DOWN",
            "REDUCE SPEED",
            YELLOW
        )

    elif prediction == "SPEED_LIMIT":

        return (
            "SPEED LIMIT",
            "CHECK SPEED",
            BLUE
        )

    elif prediction == "NO_ENTRY":

        return (
            "NO ENTRY",
            "DO NOT ENTER",
            RED
        )

    elif prediction == "GO":

        return (
            "ROAD CLEAR",
            "CONTINUE",
            GREEN
        )

    else:

        return (
            "SCANNING...",
            "NO SIGN DETECTED",
            WHITE
        )


# ==========================================
# 7. MAIN BUGGYBOT PROGRAM
# ==========================================

def main():

    print(
        "Starting BuggyBot...",
        flush=True
    )

    # Startup message
    display_message(
        "BUGGYBOT",
        "SYSTEM READY",
        GREEN
    )

    time.sleep(2)

    image_number = 1
    prediction_number = 0

    try:

        while True:

            # STEP 1: Display camera status
            display_message(
                "CAMERA ACTIVE",
                "SCANNING...",
                BLUE
            )

            # STEP 2: Capture image
            image_path = capture_image(
                image_number
            )

            # STEP 3: Simulate ML prediction
            prediction = simulated_prediction(
                image_path,
                TEST_MODE,
                prediction_number
            )

            # STEP 4: Process prediction
            line1, line2, color = (
                process_prediction(prediction)
            )

            # STEP 5: Update LCD
            display_message(
                line1,
                line2,
                color
            )

            print(
                f"LCD updated: {line1} | {line2}",
                flush=True
            )

            image_number += 1
            prediction_number += 1

            # Wait before capturing another image
            time.sleep(5)

    except KeyboardInterrupt:

        print(
            "\nStopping BuggyBot...",
            flush=True
        )

    finally:

        display_message(
            "BUGGYBOT",
            "SYSTEM OFF",
            RED
        )

        time.sleep(2)

        lcd.clear()
        lcd.setRGB(0, 0, 0)


# ==========================================
# 8. START PROGRAM
# ==========================================

if __name__ == "__main__":

    main()
