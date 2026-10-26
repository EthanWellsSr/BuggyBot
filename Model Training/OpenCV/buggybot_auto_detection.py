import cv2
import numpy as np

from pathlib import Path
from ai_edge_litert.interpreter import Interpreter


# ==========================================
# 1. CONFIGURATION
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

# Ignore very small objects
MIN_AREA = 1000

# Maximum number of candidates per frame
MAX_CANDIDATES = 10


# ==========================================
# 2. LOAD MODEL
# ==========================================

print("Loading BuggyBot model...")

interpreter = Interpreter(model_path=str(MODEL_PATH))
interpreter.allocate_tensors()

labels = LABELS_PATH.read_text().splitlines()

input_index = interpreter.get_input_details()[0]["index"]
output_index = interpreter.get_output_details()[0]["index"]

print("Model loaded successfully!")


# ==========================================
# 3. PREPROCESS IMAGE
# ==========================================

def preprocess_sign(crop):

    # Match the preprocessing used in
    # BuggyBot's existing integration script

    resized = cv2.resize(
        crop,
        (256, 256),
        interpolation=cv2.INTER_AREA
    )

    rgb = cv2.cvtColor(
        resized,
        cv2.COLOR_BGR2RGB
    )

    model_image = cv2.resize(
        rgb,
        (32, 32),
        interpolation=cv2.INTER_LINEAR
    )

    model_input = model_image.astype(
        np.float32
    )[np.newaxis]

    return model_input


# ==========================================
# 4. CLASSIFY SIGN
# ==========================================

def classify_sign(crop):

    model_input = preprocess_sign(crop)

    interpreter.set_tensor(
        input_index,
        model_input
    )

    interpreter.invoke()

    probabilities = interpreter.get_tensor(
        output_index
    )[0]

    best_index = int(np.argmax(probabilities))

    label = labels[best_index]
    confidence = float(probabilities[best_index])

    return label, confidence


# ==========================================
# 5. FIND POSSIBLE TRAFFIC SIGNS
# ==========================================

def detect_sign_candidates(frame):

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    # Reduce noise
    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    # Detect edges
    edges = cv2.Canny(
        blurred,
        50,
        150
    )

    # Close small gaps in edges
    kernel = np.ones(
        (3, 3),
        np.uint8
    )

    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        kernel
    )

    # Find object outlines
    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    frame_height, frame_width = frame.shape[:2]

    for contour in contours:

        area = cv2.contourArea(contour)

        if area < MIN_AREA:
            continue

        perimeter = cv2.arcLength(
            contour,
            True
        )

        approx = cv2.approxPolyDP(
            contour,
            0.03 * perimeter,
            True
        )

        corners = len(approx)

        # Look for roughly polygonal signs
        if corners < 3 or corners > 12:
            continue

        x, y, w, h = cv2.boundingRect(contour)

        if w == 0 or h == 0:
            continue

        aspect_ratio = w / h

        # Reject extremely wide or tall objects
        if not 0.65 <= aspect_ratio <= 1.5:
            continue

        # Add padding around detected object
        padding = int(max(w, h) * 0.10)

        x1 = max(0, x - padding)
        y1 = max(0, y - padding)

        x2 = min(frame_width, x + w + padding)
        y2 = min(frame_height, y + h + padding)

        candidates.append(
            (x1, y1, x2, y2, area)
        )

    # Prioritize larger candidates
    candidates.sort(
        key=lambda item: item[4],
        reverse=True
    )

    # Remove overlapping candidate boxes
    filtered = []

    for candidate in candidates:

        x1, y1, x2, y2, area = candidate

        overlaps = False

        for existing in filtered:

            ex1, ey1, ex2, ey2, _ = existing

            intersection_width = max(
                0,
                min(x2, ex2) - max(x1, ex1)
            )

            intersection_height = max(
                0,
                min(y2, ey2) - max(y1, ey1)
            )

            intersection = (
                intersection_width * intersection_height
            )

            candidate_area = (
                (x2 - x1) * (y2 - y1)
            )

            existing_area = (
                (ex2 - ex1) * (ey2 - ey1)
            )

            union = (
                candidate_area
                + existing_area
                - intersection
            )

            iou = (
                intersection / union
                if union > 0
                else 0
            )

            # Ignore boxes that substantially overlap
            if iou > 0.3:
                overlaps = True
                break

        if not overlaps:
            filtered.append(candidate)

        if len(filtered) >= MAX_CANDIDATES:
            break

    return filtered, edges


# ==========================================
# 6. START CAMERA
# ==========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Camera not found.")
    raise SystemExit(1)

print("Camera started.")
print("Show one or more signs to the camera.")
print("Press Q to quit.")


# ==========================================
# 7. MAIN LOOP
# ==========================================

while True:

    ret, frame = camera.read()

    if not ret:
        print("Failed to capture frame.")
        break

    candidates, edges = detect_sign_candidates(
        frame
    )

    recognized_count = 0

    # Classify every candidate
    for candidate in candidates:

        x1, y1, x2, y2, area = candidate

        crop = frame[
            y1:y2,
            x1:x2
        ]

        if crop.size == 0:
            continue

        label, confidence = classify_sign(crop)

        # Only display confident predictions
        if confidence < CONFIDENCE_THRESHOLD:
            continue

        recognized_count += 1

        # Draw bounding box
        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        # Display sign classification
        display_text = (
            f"{label}: {confidence:.1%}"
        )

        cv2.putText(
            frame,
            display_text,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    # Display number of recognized candidates
    cv2.putText(
        frame,
        f"Recognized candidates: {recognized_count}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2
    )

    cv2.imshow(
        "BuggyBot Automatic Detection",
        frame
    )

    cv2.imshow(
        "OpenCV Edge Detection",
        edges
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# 8. CLEANUP
# ==========================================

camera.release()
cv2.destroyAllWindows()

print("BuggyBot stopped.")