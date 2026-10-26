import cv2
import numpy as np

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Camera not found.")
    raise SystemExit(1)

while True:
    ret, frame = camera.read()

    if not ret:
        break

    # Convert from BGR to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Red wraps around the HSV hue scale,
    # so we need two ranges.
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])

    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([179, 255, 255])

    # Create masks for red pixels
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

    red_mask = cv2.bitwise_or(mask1, mask2)

    # Find outlines of red objects
    contours, _ = cv2.findContours(
        red_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    for contour in contours:
        area = cv2.contourArea(contour)

        # Ignore very small objects
        if area < 500:
            continue

        # Draw a rectangle around the object
        x, y, w, h = cv2.boundingRect(contour)

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

    cv2.imshow("Red Object Detection", frame)
    cv2.imshow("Red Mask", red_mask)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()