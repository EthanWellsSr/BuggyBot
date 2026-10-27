#!/usr/bin/env python3
"""CI regression check for the Pi sign demo, using the committed sign-card crops.

For every crop in Sign Cards/Test Images/cropped/<class>/<lighting>/:
  1. classify it with the combined TFLite model (the demo's classify()), and
  2. run the demo's per-class color/shape check (shape_matches()).

The baselines below are the measured results when the filters were tuned
(October 2026; see Model Training/OpenCV/OpenCV_troubleshooting_guide.md). A
change that lowers either count fails CI, so a threshold tweak that rejects
real signs is caught before it reaches BuggyBot.
"""
import importlib.util
import sys
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[2]
DEMO = REPO / "Model Training" / "OpenCV" / "pi_sign_detection_demo.py"
CROPS = REPO / "Sign Cards" / "Test Images" / "cropped"

# Measured baselines. The one shape-check miss is the very dim
# stop/no_light/stop_001.png (solidity 0.80, below the 0.9 stop rule).
MIN_CLASSIFIED = 329
MIN_SHAPE_PASS = 328


def main():
    spec = importlib.util.spec_from_file_location("demo", DEMO)
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    labels = demo.LABELS_PATH.read_text().split()
    interpreter = demo.load_interpreter(demo.MODEL_PATH)

    files = sorted(CROPS.glob("*/*/*.png"))
    if not files:
        sys.exit(f"No crops found under {CROPS}")
    classified = shape_pass = 0
    for path in files:
        truth = path.relative_to(CROPS).parts[0]
        crop = cv2.imread(str(path))
        label, confidence = demo.classify(interpreter, labels, crop)
        if label == truth:
            classified += 1
        else:
            print(f"  misclassified: {path.relative_to(REPO)} -> {label} ({confidence:.0%})")
        if demo.shape_matches(crop, truth):
            shape_pass += 1
        else:
            print(f"  shape check rejected: {path.relative_to(REPO)}")

    print(f"Classified correctly: {classified}/{len(files)} (baseline {MIN_CLASSIFIED})")
    print(f"Shape check passed:   {shape_pass}/{len(files)} (baseline {MIN_SHAPE_PASS})")
    if classified < MIN_CLASSIFIED or shape_pass < MIN_SHAPE_PASS:
        sys.exit("Regression: fewer test crops pass than the baseline.")


if __name__ == "__main__":
    main()
