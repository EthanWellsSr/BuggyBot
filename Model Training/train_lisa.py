"""Train and save the LISA (US traffic-sign) classifier."""

import csv
import math
from collections import Counter
from pathlib import Path

import tensorflow as tf


HERE = Path(__file__).resolve().parent
DATASET_ROOT = HERE / "LISA" / "prepared"
MODEL_PATH = HERE / "lisa_model.keras"
IMAGE_SIZE = (32, 32)
BATCH_SIZE = 64
SEED = 123


def load_classes() -> list[str]:
    """Return class directory names ordered by class index (from classes.csv)."""
    with (DATASET_ROOT / "classes.csv").open(newline="", encoding="utf-8") as handle:
        rows = sorted(csv.DictReader(handle), key=lambda row: int(row["class_index"]))
    return [row["class_directory"] for row in rows]


CLASSES = load_classes()
NUM_CLASSES = len(CLASSES)


def load_split(split: str) -> list[tuple[str, int]]:
    """Return (image path, class index) records for one prepared split.

    prepare_lisa.py already separated the splits by physical sign track,
    so no further splitting is needed here.
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


tf.keras.utils.set_random_seed(SEED)
train_samples = load_split("train")
validation_samples = load_split("validation")
print(f"Classes: {NUM_CLASSES}  train: {len(train_samples)}  validation: {len(validation_samples)}")
train_dataset = make_dataset(train_samples, training=True)
validation_dataset = make_dataset(validation_samples, training=False)

# LISA is very imbalanced (stop: 1,513 train crops, speed limit 65: 56), so
# rarer classes get a larger loss weight. The square root softens the effect.
counts = Counter(sample[1] for sample in train_samples)
class_weights = {
    class_id: math.sqrt(len(train_samples) / (NUM_CLASSES * count))
    for class_id, count in counts.items()
}

model = build_model()
model.fit(
    train_dataset,
    validation_data=validation_dataset,
    epochs=60,
    class_weight=class_weights,
    shuffle=False,
    verbose=2,
    callbacks=[
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
