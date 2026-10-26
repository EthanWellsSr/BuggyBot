#loads OpenCV
import cv2

# Open the laptop's default camera
camera = cv2.VideoCapture(0)

# Check whether the camera opened
if not camera.isOpened():
    print("Error: Could not open camera.")
    raise SystemExit(1)

print("Camera opened successfully!")
print("Press Q to quit.")

while True:
    # Capture a frame from the camera
    ret, frame = camera.read()

    if not ret:
        print("Failed to capture frame.")
        break

    # Display the camera image
    cv2.imshow("BuggyBot Camera Test", frame)

    # Exit when Q is pressed
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Release the camera and close windows
camera.release()
cv2.destroyAllWindows()
