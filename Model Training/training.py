"""Train and save the GTSRB traffic-sign classifier."""

import csv
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import tensorflow as tf


HERE = Path(__file__).resolve().parent
DATASET_ROOT = HERE / "GTSRB"
MODEL_PATH = HERE / "gtsrb_model.keras"
NUM_CLASSES = 43
IMAGE_SIZE = (32, 32)
BATCH_SIZE = 128
SEED = 123


def load_samples() -> list[tuple[str, int, str]]:
    """Return (image path, class ID, physical-sign track) records."""
    samples = []
    with (DATASET_ROOT / "Train.csv").open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        for row in csv.DictReader(handle):
            relative_path = Path(row["Path"])
            track = relative_path.stem.rsplit("_", 1)[0]
            samples.append(
                (str(DATASET_ROOT / relative_path), int(row["ClassId"]), track)
            )
    return samples


def split_by_track(samples):
    """Use 80% of each class's sign tracks for training and 20% for validation."""
    grouped = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        grouped[sample[1]][sample[2]].append(sample)

    training, validation = [], []
    for class_id in range(NUM_CLASSES):
        tracks = sorted(grouped[class_id])
        random.Random(SEED + class_id).shuffle(tracks)
        validation_tracks = set(tracks[: max(1, round(len(tracks) * 0.2))])

        for track, track_samples in grouped[class_id].items():
            destination = validation if track in validation_tracks else training
            destination.extend(track_samples)

    return training, validation


def make_dataset(samples, training):
    paths = [sample[0] for sample in samples]
    labels = [sample[1] for sample in samples]
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))

    if training:
        dataset = dataset.shuffle(8192, seed=SEED)

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
samples = load_samples()
train_samples, validation_samples = split_by_track(samples)
train_dataset = make_dataset(train_samples, training=True)
validation_dataset = make_dataset(validation_samples, training=False)

counts = Counter(sample[1] for sample in train_samples)
class_weights = {
    class_id: math.sqrt(len(train_samples) / (NUM_CLASSES * count))
    for class_id, count in counts.items()
}

model = build_model()
model.fit(
    train_dataset,
    validation_data=validation_dataset,
    epochs=40,
    class_weight=class_weights,
    shuffle=False,
    verbose=2,
    callbacks=[
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=7, restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=2, min_lr=1e-5
        ),
    ],
)
model.save(MODEL_PATH)
print(f"Saved model: {MODEL_PATH}")
