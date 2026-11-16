# Semester 1 Demo Resources

## Knowledge

### This project (the ground truth for every lesson)

- [OpenCV sign demo README](../../Model%20Training/OpenCV/README.md)
  What the demo does in five steps, its LCD states, options, and the 60/60
  final test. Use for: the overview and how to run it.
- [Demo source: `pi_sign_detection_demo.py`](../../Model%20Training/OpenCV/pi_sign_detection_demo.py)
  The demo itself. Use for: any claim about proposals, preprocessing,
  thresholds, the shape checks, and the SEARCHING/DISPLAYING states.
- [OpenCV troubleshooting guide](../../Model%20Training/OpenCV/OpenCV_troubleshooting_guide.md)
  Every false positive found in testing and the measurement behind each fix.
  Use for: why each rejection check exists.
- [Model Training README](../../Model%20Training/README.md)
  Datasets, the 12 classes, test scores, and the TFLite conversion. Use for:
  model facts and what each accuracy number does and does not mean.
- [Project README](../../README.md) and [Hardware README](../../Hardware/README.md)
  Current hardware, power, and test status. Use for: hardware claims.

### Background (outside sources)

- [Stanford CS231n: Convolutional Neural Networks](https://cs231n.github.io/convolutional-networks/)
  Standard course notes on CNNs. Use for: what the classifier is, for readers
  who want more than one paragraph.
- [OpenCV: Contours, Getting Started](https://docs.opencv.org/4.x/d4/d73/tutorial_py_contours_begin.html)
  Official tutorial on finding outlines in a binary image. Use for: how the
  proposal stage finds candidate regions.
- [Google: LiteRT overview](https://ai.google.dev/edge/litert)
  The on-device runtime (formerly TensorFlow Lite) the CM5 uses. Use for: why
  the Pi runs a `.tflite` file instead of full TensorFlow.
- [Raspberry Pi: Compute Module documentation](https://www.raspberrypi.com/documentation/computers/compute-module.html)
  Official CM5 and IO Board docs. Use for: hardware background.

## Wisdom (Communities)

- The BuggyBot team and the CENG 4265 advisor. Use for: questions about why a
  design choice was made.
- [Raspberry Pi Forums](https://forums.raspberrypi.com/)
  Official, moderated. Use for: CM5, camera, and Picamera2 questions.
- [OpenCV Forum](https://forum.opencv.org/)
  Official OpenCV community. Use for: proposal and shape-check questions.

## Gaps

- No measurements yet for distance, viewing angle, or other lighting.
