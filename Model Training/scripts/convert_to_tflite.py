"""Convert the combined model to TensorFlow Lite for BuggyBot's CM5.

Full TensorFlow is large and slow to install on the Pi; the LiteRT runtime
(ai-edge-litert) runs a .tflite file with far fewer dependencies. The
conversion keeps float32 weights, so predictions should match the Keras model.
This script checks that on the committed sign-card photo crops, then saves
models/combined_model.tflite and models/combined_model_labels.txt (one class
label per line, in output order; the Pi has no copy of data/).
"""

import csv
import json
from pathlib import Path

import numpy as np
import tensorflow as tf


ROOT = Path(__file__).resolve().parents[1]
KERAS_MODEL = ROOT / "models" / "combined_model.keras"
TRAINING_REPORT = ROOT / "reports" / "combined_training_report.json"
TFLITE_MODEL = ROOT / "models" / "combined_model.tflite"
LABELS_FILE = ROOT / "models" / "combined_model_labels.txt"
CROPS = ROOT.parent / "Sign Cards" / "Test Images" / "cropped"


def load_crops():
    with (CROPS / "manifest.csv").open(newline="", encoding="utf-8") as handle:
        paths = [CROPS / row["output_file"] for row in csv.DictReader(handle)]
    images = [
        tf.image.resize(tf.io.decode_png(tf.io.read_file(str(path)), channels=3), (32, 32))
        for path in paths
    ]
    return np.stack(images).astype(np.float32)


def main():
    model = tf.keras.models.load_model(KERAS_MODEL, compile=False)
    converted = tf.lite.TFLiteConverter.from_keras_model(model).convert()

    # Compare both models on the same images before trusting the conversion.
    images = load_crops()
    keras_probabilities = model.predict(images, verbose=0)
    interpreter = tf.lite.Interpreter(model_content=converted)
    interpreter.allocate_tensors()
    input_index = interpreter.get_input_details()[0]["index"]
    output_index = interpreter.get_output_details()[0]["index"]
    lite_probabilities = []
    for image in images:
        interpreter.set_tensor(input_index, image[None])
        interpreter.invoke()
        lite_probabilities.append(interpreter.get_tensor(output_index)[0])
    lite_probabilities = np.stack(lite_probabilities)

    same = (keras_probabilities.argmax(1) == lite_probabilities.argmax(1)).mean()
    largest = np.abs(keras_probabilities - lite_probabilities).max()
    print(f"Same prediction on {same:.1%} of {len(images)} crops; "
          f"largest probability difference {largest:.2e}")
    if same < 1.0:
        raise SystemExit("TFLite predictions differ from Keras; not saving")

    labels = json.loads(TRAINING_REPORT.read_text(encoding="utf-8"))["class_labels"]
    TFLITE_MODEL.write_bytes(converted)
    LABELS_FILE.write_text("\n".join(labels) + "\n", encoding="utf-8")
    print(f"Saved {TFLITE_MODEL} ({len(converted) / 1024:.0f} KB) and {LABELS_FILE}")


if __name__ == "__main__":
    main()
