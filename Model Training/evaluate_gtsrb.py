"""Evaluate the saved model on the independent GTSRB test set."""

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
import tensorflow as tf


HERE = Path(__file__).resolve().parent
DATASET_ROOT = HERE / "GTSRB"
MODEL_PATH = HERE / "gtsrb_model.keras"
RESULTS_PATH = HERE / "gtsrb_test_results.json"
NUM_CLASSES = 43
BATCH_SIZE = 128


paths, labels = [], []
with (DATASET_ROOT / "Test.csv").open(
    newline="", encoding="utf-8-sig"
) as handle:
    for row in csv.DictReader(handle):
        paths.append(str(DATASET_ROOT / row["Path"]))
        labels.append(int(row["ClassId"]))


def load_image(path, label):
    image = tf.io.decode_png(tf.io.read_file(path), channels=3)
    image = tf.image.resize(image, (32, 32))
    return image, label


dataset = (
    tf.data.Dataset.from_tensor_slices((paths, labels))
    .map(load_image, num_parallel_calls=tf.data.AUTOTUNE)
    .batch(BATCH_SIZE)
    .prefetch(tf.data.AUTOTUNE)
)

model = tf.keras.models.load_model(MODEL_PATH)
probabilities = model.predict(dataset, verbose=0)
labels = np.asarray(labels)
predictions = probabilities.argmax(axis=1)
correct = predictions == labels

top3_predictions = np.argpartition(probabilities, -3, axis=1)[:, -3:]
top3_correct = np.any(top3_predictions == labels[:, None], axis=1)

class_totals = Counter(labels.tolist())
class_correct = Counter(labels[correct].tolist())
per_class = {
    str(class_id): {
        "correct": class_correct[class_id],
        "total": class_totals[class_id],
        "accuracy": class_correct[class_id] / class_totals[class_id],
    }
    for class_id in range(NUM_CLASSES)
}

confusions = Counter(
    (int(actual), int(predicted))
    for actual, predicted in zip(labels[~correct], predictions[~correct])
)

results = {
    "images": len(labels),
    "top1_accuracy": float(correct.mean()),
    "top3_accuracy": float(top3_correct.mean()),
    "macro_class_accuracy": float(
        np.mean([result["accuracy"] for result in per_class.values()])
    ),
    "correct": int(correct.sum()),
    "incorrect": int((~correct).sum()),
    "per_class": per_class,
    "common_confusions": [
        {"actual": actual, "predicted": predicted, "count": count}
        for (actual, predicted), count in confusions.most_common(10)
    ],
}

RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

print(f"Images: {results['images']}")
print(f"Top-1 accuracy: {results['top1_accuracy']:.4%}")
print(f"Top-3 accuracy: {results['top3_accuracy']:.4%}")
print(f"Macro class accuracy: {results['macro_class_accuracy']:.4%}")
print(f"Correct / incorrect: {results['correct']} / {results['incorrect']}")
print(f"Saved results: {RESULTS_PATH}")
