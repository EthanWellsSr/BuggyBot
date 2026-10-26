import cv2

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Camera not found.")
    raise SystemExit(1)

while True:
    ret, frame = camera.read()

    if not ret:
        break

    # 1. Convert the image to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 2. Resize the image
    resized = cv2.resize(frame, (320, 240))

    # 3. Crop the center of the image
    height, width = frame.shape[:2]

    crop = frame[
        height // 4 : 3 * height // 4,
        width // 4 : 3 * width // 4
    ]

    # Display the results
    cv2.imshow("Original Camera", frame)
    cv2.imshow("Grayscale", gray)
    cv2.imshow("Resized", resized)
    cv2.imshow("Cropped", crop)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()