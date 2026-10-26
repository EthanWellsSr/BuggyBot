import cv2
import numpy as np

# Open laptop webcam
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Camera not found.")
    raise SystemExit(1)

while True:
    ret, frame = camera.read()

    if not ret:
        print("Failed to capture frame.")
        break

    # STEP 1: Convert camera image to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # STEP 2: Define red color ranges
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])

    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([179, 255, 255])

    # STEP 3: Create red mask
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

    red_mask = cv2.bitwise_or(mask1, mask2)

    # STEP 4: Find red objects
    contours, _ = cv2.findContours(
        red_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    # Find the largest red object
    largest_contour = None
    largest_area = 500

    for contour in contours:
        area = cv2.contourArea(contour)

        if area > largest_area:
            largest_area = area
            largest_contour = contour

    # STEP 5: Extract potential traffic sign
    if largest_contour is not None:

        x, y, w, h = cv2.boundingRect(largest_contour)

        # Draw bounding box
        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

        # Crop detected object
        cropped_sign = frame[y:y+h, x:x+w]

        # STEP 6: Resize extracted image
        resized_sign = cv2.resize(
            cropped_sign,
            (224, 224)
        )

        # STEP 7: Normalize image
        normalized_sign = resized_sign.astype(np.float32) / 255.0

        # Display extracted sign
        cv2.imshow("Extracted Sign", resized_sign)

        # Print image shape once per detected frame
        # (224, 224, 3)
        # print(normalized_sign.shape)

    # Display original camera and mask
    cv2.imshow("Camera", frame)
    cv2.imshow("Red Mask", red_mask)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()