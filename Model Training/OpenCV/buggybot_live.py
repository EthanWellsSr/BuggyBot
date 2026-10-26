import cv2
import numpy as np

from pathlib import Path
from ai_edge_litert.interpreter import Interpreter


# ==========================================
# 1. MODEL CONFIGURATION
# ==========================================

MODEL_FOLDER = (
    Path.home()
    / "Projects"
    / "BuggyBot"
    / "Model Training"
    / "models"
)

MODEL_PATH = MODEL_FOLDER / "combined_model.tflite"
LABELS_PATH = MODEL_FOLDER / "combined_model_labels.txt"

CONFIDENCE_THRESHOLD = 0.80


# ==========================================
# 2. LOAD TRAINED MODEL
# ==========================================

print("Loading BuggyBot model...")

interpreter = Interpreter(model_path=str(MODEL_PATH))
interpreter.allocate_tensors()

labels = LABELS_PATH.read_text().splitlines()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

input_index = input_details[0]["index"]
output_index = output_details[0]["index"]

print("Model loaded successfully!")
print("Recognized classes:", labels)


# ==========================================
# 3. START WEBCAM
# ==========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Camera not found.")
    raise SystemExit(1)

print("Camera started.")
print("Hold a traffic sign inside the green square.")
print("Press Q to quit.")


# ==========================================
# 4. LIVE RECOGNITION LOOP
# ==========================================

while True:

    ret, frame = camera.read()

    if not ret:
        print("Failed to capture frame.")
        break

    height, width = frame.shape[:2]

    # --------------------------------------
    # STEP A: CREATE REGION OF INTEREST
    # --------------------------------------

    side = round(0.18 * width)

    center_x = round(0.52 * width)
    center_y = round(0.49 * height)

    x = max(0, min(center_x - side // 2, width - side))
    y = max(0, min(center_y - side // 2, height - side))

    cropped_sign = frame[
        y:y + side,
        x:x + side
    ]

    # --------------------------------------
    # STEP B: OPENCV PREPROCESSING
    # --------------------------------------

    processed_sign = cv2.resize(
        cropped_sign,
        (256, 256),
        interpolation=cv2.INTER_AREA
    )

    rgb_sign = cv2.cvtColor(
        processed_sign,
        cv2.COLOR_BGR2RGB
    )

    model_image = cv2.resize(
        rgb_sign,
        (32, 32),
        interpolation=cv2.INTER_LINEAR
    )

    model_input = model_image.astype(
        np.float32
    )[np.newaxis]

    # --------------------------------------
    # STEP C: TENSORFLOW LITE PREDICTION
    # --------------------------------------

    interpreter.set_tensor(input_index, model_input)

    interpreter.invoke()

    probabilities = interpreter.get_tensor(
        output_index
    )[0]

    best_index = int(np.argmax(probabilities))

    predicted_label = labels[best_index]
    confidence = float(probabilities[best_index])

    # --------------------------------------
    # STEP D: PROCESS PREDICTION
    # --------------------------------------

    if confidence >= CONFIDENCE_THRESHOLD:

        display_text = predicted_label

        display_confidence = (
            f"Confidence: {confidence:.1%}"
        )

        box_color = (0, 255, 0)

    else:

        display_text = "SCANNING..."

        display_confidence = (
            f"Top score: {confidence:.1%}"
        )

        box_color = (0, 255, 255)

    # --------------------------------------
    # STEP E: DISPLAY RESULTS
    # --------------------------------------

    cv2.rectangle(
        frame,
        (x, y),
        (x + side, y + side),
        box_color,
        2
    )

    cv2.putText(
        frame,
        display_text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        box_color,
        2
    )

    cv2.putText(
        frame,
        display_confidence,
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        box_color,
        2
    )

    cv2.imshow("BuggyBot Live Recognition", frame)

    cv2.imshow("Extracted Sign", processed_sign)

    # --------------------------------------
    # STEP F: EXIT
    # --------------------------------------

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# 5. CLEANUP
# ==========================================

camera.release()
cv2.destroyAllWindows()

print("BuggyBot stopped.")