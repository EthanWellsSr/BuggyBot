import sys
import time
from pathlib import Path

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter
from libcamera import controls
from picamera2 import Picamera2

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

# "manual": press Enter to capture each frame
# "automatic": capture continuously
TEST_MODE = "manual"

# Seconds between frames in automatic mode
AUTOMATIC_DELAY = 1.0

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

# Trained sign classifier (converted to TensorFlow Lite)
MODEL_FOLDER = (
    Path(__file__).resolve().parents[2]
    / "Model Training"
    / "models"
)
MODEL_PATH = MODEL_FOLDER / "combined_model.tflite"
LABELS_PATH = MODEL_FOLDER / "combined_model_labels.txt"

# Camera frame size (full field of view, 2x2 binned)
FRAME_SIZE = (2304, 1296)

# Region of interest: the square the sign card must fill.
# Center and width are fractions of the frame width/height.
# Defaults come from the median sign position in the
# 329 sign-card test photos. Every saved frame shows
# this box in green so the card can be lined up.
ROI_CENTER_X = 0.52
ROI_CENTER_Y = 0.49
ROI_WIDTH = 0.18

# Below this confidence the LCD shows "SCANNING..."
# instead of a sign. The model always picks one of its
# 12 classes, even when no sign is in the box.
CONFIDENCE_THRESHOLD = 0.80


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
# 4. CAMERA FUNCTIONS
# ==========================================

def start_camera():

    camera = Picamera2()

    # RGB888 frames arrive in BGR byte order,
    # which is what OpenCV expects
    config = camera.create_still_configuration(
        main={
            "size": FRAME_SIZE,
            "format": "RGB888"
        }
    )

    camera.configure(config)

    # Camera Module 3 has autofocus
    camera.set_controls(
        {"AfMode": controls.AfModeEnum.Continuous}
    )

    camera.start()

    # Let exposure, white balance, and focus settle
    time.sleep(2)

    return camera


def capture_frame(camera):

    return camera.capture_array("main")


# ==========================================
# 5. OPENCV REGION OF INTEREST
# ==========================================

def roi_box(frame):

    height, width = frame.shape[:2]

    side = round(ROI_WIDTH * width)

    left = round(ROI_CENTER_X * width - side / 2)
    top = round(ROI_CENTER_Y * height - side / 2)

    # Keep the box inside the frame
    left = min(max(left, 0), width - side)
    top = min(max(top, 0), height - side)

    return left, top, side


def crop_sign(frame):

    left, top, side = roi_box(frame)

    crop = frame[
        top:top + side,
        left:left + side
    ]

    # Same steps as the tested crops: shrink to 256 px
    # with area averaging, then to the model's 32x32
    crop = cv2.resize(
        crop,
        (256, 256),
        interpolation=cv2.INTER_AREA
    )

    return crop


# ==========================================
# 6. MACHINE LEARNING MODEL
# ==========================================

def load_model():

    interpreter = Interpreter(model_path=str(MODEL_PATH))
    interpreter.allocate_tensors()

    labels = LABELS_PATH.read_text().split()

    return interpreter, labels


def predict_sign(interpreter, labels, crop):

    # The model was trained on RGB images with 0-255
    # values; it rescales internally
    image = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    image = cv2.resize(
        image,
        (32, 32),
        interpolation=cv2.INTER_LINEAR
    )
    image = image.astype(np.float32)[np.newaxis]

    input_index = interpreter.get_input_details()[0]["index"]
    output_index = interpreter.get_output_details()[0]["index"]

    interpreter.set_tensor(input_index, image)
    interpreter.invoke()

    probabilities = interpreter.get_tensor(output_index)[0]
    best = int(np.argmax(probabilities))

    return labels[best], float(probabilities[best])


def save_images(frame, crop, image_number, label, confidence):

    left, top, side = roi_box(frame)

    # Draw the region of interest on a copy of the frame
    annotated = frame.copy()
    cv2.rectangle(
        annotated,
        (left, top),
        (left + side, top + side),
        (0, 255, 0),
        4
    )
    cv2.putText(
        annotated,
        f"{label} {confidence:.0%}",
        (left, max(top - 15, 30)),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 255, 0),
        3
    )

    name = f"image_{image_number:04d}"
    cv2.imwrite(str(IMAGE_FOLDER / f"{name}_frame.jpg"), annotated)
    cv2.imwrite(str(IMAGE_FOLDER / f"{name}_crop.png"), crop)

    return IMAGE_FOLDER / f"{name}_frame.jpg"


# ==========================================
# 7. DECISION LOGIC
# ==========================================

SIGN_MESSAGES = {
    "addedLane": ("ADDED LANE", "LANE AHEAD", YELLOW),
    "keepRight": ("KEEP RIGHT", "STAY RIGHT", WHITE),
    "merge": ("MERGE", "MERGE AHEAD", YELLOW),
    "pedestrianCrossing": ("PED CROSSING", "WATCH PEDS", YELLOW),
    "school": ("SCHOOL ZONE", "SLOW DOWN", YELLOW),
    "signalAhead": ("SIGNAL AHEAD", "GET READY", YELLOW),
    "speedLimit25": ("SPEED LIMIT 25", "MAX 25", BLUE),
    "speedLimit30": ("SPEED LIMIT 30", "MAX 30", BLUE),
    "speedLimit35": ("SPEED LIMIT 35", "MAX 35", BLUE),
    "speedLimit45": ("SPEED LIMIT 45", "MAX 45", BLUE),
    "speedLimit65": ("SPEED LIMIT 65", "MAX 65", BLUE),
    "stop": ("STOP SIGN", "STOP", RED),
}


def process_prediction(label, confidence):

    if confidence < CONFIDENCE_THRESHOLD:

        return (
            "SCANNING...",
            "NO SIGN DETECTED",
            WHITE
        )

    line1, line2, color = SIGN_MESSAGES[label]

    # Show confidence at the end of line 2
    # (actions are at most 11 characters)
    line2 = f"{line2:<12}{confidence:>4.0%}"

    return line1, line2, color


# ==========================================
# 8. MAIN BUGGYBOT PROGRAM
# ==========================================

def main():

    print(
        "Starting BuggyBot...",
        flush=True
    )

    # Startup message
    display_message(
        "BUGGYBOT",
        "LOADING MODEL",
        GREEN
    )

    interpreter, labels = load_model()
    camera = start_camera()

    display_message(
        "BUGGYBOT",
        "SYSTEM READY",
        GREEN
    )

    time.sleep(2)

    image_number = 1

    try:

        while True:

            if TEST_MODE == "manual":

                input("\nPress Enter to capture (Ctrl+C to quit)...")

            # STEP 1: Display camera status
            display_message(
                "CAMERA ACTIVE",
                "SCANNING...",
                BLUE
            )

            # STEP 2: Capture frame
            start = time.perf_counter()
            frame = capture_frame(camera)
            captured = time.perf_counter()

            # STEP 3: Crop the region of interest
            crop = crop_sign(frame)

            # STEP 4: Run the model
            label, confidence = predict_sign(
                interpreter,
                labels,
                crop
            )
            predicted = time.perf_counter()

            print(
                f"Prediction: {label} ({confidence:.1%})  "
                f"capture {1000 * (captured - start):.0f} ms, "
                f"crop + model {1000 * (predicted - captured):.0f} ms",
                flush=True
            )

            # STEP 5: Process prediction
            line1, line2, color = process_prediction(
                label,
                confidence
            )

            # STEP 6: Update LCD
            display_message(
                line1,
                line2,
                color
            )

            print(
                f"LCD updated: {line1} | {line2}",
                flush=True
            )

            # STEP 7: Save the frame (with the box) and crop
            saved = save_images(
                frame,
                crop,
                image_number,
                label,
                confidence
            )

            print(
                f"Saved: {saved}",
                flush=True
            )

            image_number += 1

            if TEST_MODE == "automatic":

                time.sleep(AUTOMATIC_DELAY)

    except KeyboardInterrupt:

        print(
            "\nStopping BuggyBot...",
            flush=True
        )

    finally:

        camera.stop()

        display_message(
            "BUGGYBOT",
            "SYSTEM OFF",
            RED
        )

        time.sleep(2)

        lcd.clear()
        lcd.setRGB(0, 0, 0)


# ==========================================
# 9. START PROGRAM
# ==========================================

if __name__ == "__main__":

    main()
