"""Train a Mapillary-only classifier and save its evaluation in one report."""

import csv
import json
import math
import time
from collections import Counter
from pathlib import Path

import numpy as np
import tensorflow as tf


HERE = Path(__file__).resolve().parent
DATASET_ROOT = HERE / "LISA" / "mapillary_prepared"
MODEL_PATH = HERE / "mapillary_model.keras"
REPORT_PATH = HERE / "mapillary_training_report.json"
IMAGE_SIZE = (32, 32)
BATCH_SIZE = 64
MAX_EPOCHS = 60
SEED = 123


with (DATASET_ROOT / "classes.csv").open(newline="", encoding="utf-8") as handle:
    class_rows = sorted(csv.DictReader(handle), key=lambda row: int(row["class_index"]))
CLASSES = [row["class_directory"] for row in class_rows]
LABELS = [row["label"] for row in class_rows]
NUM_CLASSES = len(CLASSES)

with (DATASET_ROOT / "manifest.csv").open(newline="", encoding="utf-8") as handle:
    manifest = {row["output_file"]: row for row in csv.DictReader(handle)}
dataset_summary = json.loads((DATASET_ROOT / "summary.json").read_text(encoding="utf-8"))


def load_split(split: str) -> list[tuple[str, int]]:
    """Return (image path, class index) records for one prepared split.

    prepare_mapillary.py already assigned splits by source image. It cannot
    identify the same physical sign across different source images.
    """
    samples = []
    for class_id, class_directory in enumerate(CLASSES):
        for path in sorted((DATASET_ROOT / split / class_directory).glob("*.png")):
            samples.append((str(path), class_id))
    return samples


def make_dataset(samples, training):
    paths = [sample[0] for sample in samples]
    labels = [sample[1] for sample in samples]
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))

    if training:
        dataset = dataset.shuffle(len(samples), seed=SEED)

    def load_image(path, label):
        image = tf.io.decode_png(tf.io.read_file(path), channels=3)
        image = tf.image.resize(image, IMAGE_SIZE)
        return image, label

    return (
        dataset.map(load_image, num_parallel_calls=tf.data.AUTOTUNE)
        .batch(BATCH_SIZE)
        .prefetch(tf.data.AUTOTUNE)
    )


def build_model():
    augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomRotation(0.06, fill_mode="nearest"),
            tf.keras.layers.RandomTranslation(0.08, 0.08, fill_mode="nearest"),
            tf.keras.layers.RandomZoom(0.10, fill_mode="nearest"),
            tf.keras.layers.RandomContrast(0.15),
            tf.keras.layers.RandomBrightness(0.12, value_range=(0.0, 1.0)),
        ]
    )

    inputs = tf.keras.Input(shape=(32, 32, 3))
    x = tf.keras.layers.Rescaling(1.0 / 255)(inputs)
    x = augmentation(x)

    for filters, dropout in ((32, 0.10), (64, 0.20)):
        for _ in range(2):
            x = tf.keras.layers.Conv2D(
                filters, 3, padding="same", use_bias=False
            )(x)
            x = tf.keras.layers.BatchNormalization()(x)
            x = tf.keras.layers.Activation("relu")(x)
        x = tf.keras.layers.MaxPooling2D()(x)
        x = tf.keras.layers.Dropout(dropout)(x)

    x = tf.keras.layers.Conv2D(128, 3, padding="same", use_bias=False)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Activation("relu")(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.40)(x)
    outputs = tf.keras.layers.Dense(NUM_CLASSES, activation="softmax")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


class EpochRecorder(tf.keras.callbacks.Callback):
    """Record the numeric epoch output, learning rate, and duration."""

    def __init__(self):
        super().__init__()
        self.epochs = []

    def on_epoch_begin(self, epoch, logs=None):
        self.started = time.perf_counter()
        self.learning_rate = float(tf.keras.backend.get_value(self.model.optimizer.learning_rate))

    def on_epoch_end(self, epoch, logs=None):
        self.epochs.append({
            "epoch": epoch + 1,
            "seconds": round(time.perf_counter() - self.started, 2),
            "learning_rate": self.learning_rate,
            **{name: float(value) for name, value in (logs or {}).items()},
        })


def split_summary(samples):
    counts = Counter(class_id for _, class_id in samples)
    source_images = {label: set() for label in LABELS}
    for path, class_id in samples:
        relative_path = Path(path).relative_to(DATASET_ROOT).as_posix()
        source_images[LABELS[class_id]].add(manifest[relative_path]["image_key"])
    return {
        "crops": len(samples),
        "source_images": len({image for images in source_images.values() for image in images}),
        "per_class": {
            label: {"crops": counts[class_id], "source_images": len(source_images[label])}
            for class_id, label in enumerate(LABELS)
        },
    }


def evaluate_split(model, samples):
    probabilities = model.predict(make_dataset(samples, training=False), verbose=0)
    actual = np.asarray([class_id for _, class_id in samples])
    predicted = probabilities.argmax(axis=1)
    correct = actual == predicted
    top_k = min(3, NUM_CLASSES)
    top_predictions = np.argsort(probabilities, axis=1)[:, -top_k:]
    top_correct = np.any(top_predictions == actual[:, None], axis=1)

    # Confusion matrix rows are actual classes; columns are predicted classes.
    confusion = np.zeros((NUM_CLASSES, NUM_CLASSES), dtype=int)
    np.add.at(confusion, (actual, predicted), 1)
    per_class = {}
    for class_id, label in enumerate(LABELS):
        true_positive = int(confusion[class_id, class_id])
        support = int(confusion[class_id].sum())
        predicted_count = int(confusion[:, class_id].sum())
        precision = true_positive / predicted_count if predicted_count else 0.0
        recall = true_positive / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "support": support,
            "correct": true_positive,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    errors = []
    source_image_errors = Counter()
    source_image_totals = Counter()
    for index, (path, class_id) in enumerate(samples):
        relative_path = Path(path).relative_to(DATASET_ROOT).as_posix()
        source = manifest[relative_path]
        image_key = source["image_key"]
        source_image_totals[image_key] += 1
        if correct[index]:
            continue
        source_image_errors[image_key] += 1
        top_ids = np.argsort(probabilities[index])[-top_k:][::-1]
        errors.append({
            "image": relative_path,
            "source_image": source["source_image"],
            "image_key": image_key,
            "object_key": source["object_key"],
            "original_split": source["original_split"],
            "mapillary_label": source["mapillary_label"],
            "occluded": source["occluded"].lower() == "true",
            "source_box_width": float(source["source_x_max"]) - float(source["source_x_min"]),
            "source_box_height": float(source["source_y_max"]) - float(source["source_y_min"]),
            "actual": LABELS[class_id],
            "predicted": LABELS[int(predicted[index])],
            "predicted_probability": float(probabilities[index, predicted[index]]),
            "actual_probability": float(probabilities[index, class_id]),
            "top_predictions": [
                {"label": LABELS[int(candidate)], "probability": float(probabilities[index, candidate])}
                for candidate in top_ids
            ],
        })

    confusion_pairs = [
        {"actual": LABELS[row], "predicted": LABELS[column], "count": int(confusion[row, column])}
        for row in range(NUM_CLASSES)
        for column in range(NUM_CLASSES)
        if row != column and confusion[row, column]
    ]
    confusion_pairs.sort(key=lambda item: item["count"], reverse=True)
    errors.sort(key=lambda item: item["predicted_probability"], reverse=True)
    return {
        "images": len(samples),
        "loss": float(np.mean(-np.log(np.clip(probabilities[np.arange(len(actual)), actual], 1e-7, 1.0)))),
        "top1_accuracy": float(correct.mean()),
        "top3_accuracy": float(top_correct.mean()),
        "macro_precision": float(np.mean([row["precision"] for row in per_class.values()])),
        "macro_recall": float(np.mean([row["recall"] for row in per_class.values()])),
        "macro_class_accuracy": float(np.mean([row["recall"] for row in per_class.values()])),
        "macro_f1": float(np.mean([row["f1"] for row in per_class.values()])),
        "correct": int(correct.sum()),
        "incorrect": int((~correct).sum()),
        "per_class": per_class,
        "confusion_matrix": confusion.tolist(),
        "common_confusions": confusion_pairs,
        "error_source_images": [
            {"image_key": image_key, "incorrect": count, "total": source_image_totals[image_key]}
            for image_key, count in source_image_errors.most_common()
        ],
        "errors": errors,
    }


tf.keras.utils.set_random_seed(SEED)
samples = {split: load_split(split) for split in ("train", "validation", "test")}
print(
    f"Classes: {NUM_CLASSES}  train: {len(samples['train'])}  "
    f"validation: {len(samples['validation'])}  test: {len(samples['test'])}"
)
train_dataset = make_dataset(samples["train"], training=True)
validation_dataset = make_dataset(samples["validation"], training=False)

# Mapillary is imbalanced (stop: 827 train crops, speed limit 65: 19), so
# rarer classes get a larger loss weight. The square root softens the effect.
counts = Counter(sample[1] for sample in samples["train"])
class_weights = {
    class_id: math.sqrt(len(samples["train"]) / (NUM_CLASSES * count))
    for class_id, count in counts.items()
}

model = build_model()
recorder = EpochRecorder()
model.fit(
    train_dataset,
    validation_data=validation_dataset,
    epochs=MAX_EPOCHS,
    class_weight=class_weights,
    verbose=2,
    callbacks=[
        recorder,
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=10, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=3, min_lr=1e-5
        ),
    ],
)
model.save(MODEL_PATH)
print(f"Saved model: {MODEL_PATH}")

report = {
    "model_file": MODEL_PATH.name,
    "dataset": "Mapillary prepared 12-class subset",
    "dataset_summary": dataset_summary,
    "class_labels": LABELS,
    "training_config": {
        "seed": SEED,
        "image_size": list(IMAGE_SIZE),
        "batch_size": BATCH_SIZE,
        "max_epochs": MAX_EPOCHS,
        "optimizer": "Adam",
        "initial_learning_rate": 1e-3,
        "loss": "sparse_categorical_crossentropy",
        "training_loss_uses_class_weights": True,
        "validation_and_test_loss_use_class_weights": False,
        "class_weights": {LABELS[class_id]: weight for class_id, weight in class_weights.items()},
        "early_stopping": {"monitor": "val_loss", "patience": 10, "restore_best_weights": True},
        "reduce_lr_on_plateau": {"monitor": "val_loss", "factor": 0.5, "patience": 3, "min_lr": 1e-5},
        "model_parameters": model.count_params(),
        "model_architecture": json.loads(model.to_json()),
    },
    "splits": {split: split_summary(rows) for split, rows in samples.items()},
    "epochs": recorder.epochs,
    "best_epoch_by_validation_loss": min(recorder.epochs, key=lambda row: row["val_loss"])["epoch"],
    "epochs_completed": len(recorder.epochs),
    "validation": evaluate_split(model, samples["validation"]),
    "test": evaluate_split(model, samples["test"]),
}
REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
for split in ("validation", "test"):
    result = report[split]
    print(
        f"{split}: top-1 {result['top1_accuracy']:.2%}, top-3 {result['top3_accuracy']:.2%}, "
        f"macro F1 {result['macro_f1']:.2%}, {result['incorrect']} errors"
    )
print(f"Saved report: {REPORT_PATH}")
