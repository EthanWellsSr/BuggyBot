"""Score the US-sign models on BuggyBot camera photos of the printed sign cards.

Reads the crops made by crop_sign_photos.py from
Sign Cards/Test Images/cropped/<class>/<condition>/*.png, shuffles them into a
random (seeded) order, and runs the LISA, Mapillary, and combined models on
them. Writes reports/sign_photo_test_report.json and a readable
reports/sign_photo_test_results.md with accuracy overall, per class, and per
lighting condition, plus every mistake.

These are photos of printed cards from the car's own camera, so unlike the
road-scene test sets they show how the models handle BuggyBot's camera.
"""

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
import tensorflow as tf


ROOT = Path(__file__).resolve().parents[1]
CROPS = ROOT.parent / "Sign Cards" / "Test Images" / "cropped"
CLASSES_FILE = ROOT / "data" / "prepared" / "combined" / "classes.csv"
REPORT_PATH = ROOT / "reports" / "sign_photo_test_report.json"
SUMMARY_PATH = ROOT / "reports" / "sign_photo_test_results.md"
MODELS = {
    "lisa": (ROOT / "models" / "lisa_model.keras", ROOT / "reports" / "lisa_training_report.json"),
    "mapillary": (ROOT / "models" / "mapillary_model.keras", ROOT / "reports" / "mapillary_training_report.json"),
    "combined": (ROOT / "models" / "combined_model.keras", ROOT / "reports" / "combined_training_report.json"),
}
IMAGE_SIZE = (32, 32)
SEED = 123


def load_photos(labels):
    with (CROPS / "manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row["sign_class"] not in labels:
            raise ValueError(f"{row['output_file']}: unknown class {row['sign_class']}")
        if not (CROPS / row["output_file"]).is_file():
            raise FileNotFoundError(CROPS / row["output_file"])

    # Shuffle so photos are not fed class by class. This does not change any
    # score (the models predict each image independently), but it guarantees
    # the results cannot depend on the order the photos were taken in.
    order = np.random.default_rng(SEED).permutation(len(rows))
    return [rows[index] for index in order]


def make_dataset(rows):
    # Same preprocessing as training: decode PNG, resize to 32x32, 0-255 floats.
    def load_image(path):
        image = tf.io.decode_png(tf.io.read_file(path), channels=3)
        return tf.image.resize(image, IMAGE_SIZE)

    paths = [str(CROPS / row["output_file"]) for row in rows]
    return tf.data.Dataset.from_tensor_slices(paths).map(load_image).batch(64)


def accuracy(actual, predicted, mask=None):
    if mask is not None:
        actual, predicted = actual[mask], predicted[mask]
    return {"images": int(len(actual)), "correct": int((actual == predicted).sum()),
            "accuracy": float((actual == predicted).mean()) if len(actual) else 0.0}


def evaluate(rows, probabilities, labels):
    actual = np.asarray([labels.index(row["sign_class"]) for row in rows])
    predicted = probabilities.argmax(axis=1)
    top3 = np.argsort(probabilities, axis=1)[:, -3:]
    classes = sorted({row["sign_class"] for row in rows}, key=labels.index)
    conditions = sorted({row["condition"] for row in rows})
    confusions = Counter(
        (labels[a], labels[p]) for a, p in zip(actual, predicted) if a != p
    )
    return {
        "overall": accuracy(actual, predicted)
        | {"top3_accuracy": float(np.any(top3 == actual[:, None], axis=1).mean())},
        "by_class": {
            name: accuracy(actual, predicted, actual == labels.index(name)) for name in classes
        },
        "by_condition": {
            name: accuracy(actual, predicted, np.asarray([row["condition"] == name for row in rows]))
            for name in conditions
        },
        "common_confusions": [
            {"actual": a, "predicted": p, "count": count} for (a, p), count in confusions.most_common()
        ],
        "errors": [
            {
                "image": row["output_file"],
                "actual": row["sign_class"],
                "predicted": labels[predicted[index]],
                "predicted_probability": float(probabilities[index, predicted[index]]),
                "actual_probability": float(probabilities[index, actual[index]]),
            }
            for index, row in enumerate(rows)
            if actual[index] != predicted[index]
        ],
    }


def percent(value):
    return f"{100 * value:.1f}%"


def markdown(report):
    names = list(report["models"])
    lines = [
        "# Sign-card photo test",
        "",
        f"{report['images']} BuggyBot camera photos of the printed sign cards, cropped by",
        "`scripts/crop_sign_photos.py`, shuffled (seed "
        f"{report['shuffle_seed']}), and classified by each US-sign model.",
        "Only the classes photographed so far are included.",
        "",
        "| Model | Top-1 | Top-3 |",
        "| --- | ---: | ---: |",
    ]
    for name in names:
        overall = report["models"][name]["overall"]
        lines.append(f"| {name} | {percent(overall['accuracy'])} ({overall['correct']}/{overall['images']}) "
                     f"| {percent(overall['top3_accuracy'])} |")
    lines += ["", "## Accuracy by sign", "", "| Sign | Photos | " + " | ".join(names) + " |",
              "| --- | ---: |" + " ---: |" * len(names)]
    for sign, result in report["models"][names[0]]["by_class"].items():
        cells = [percent(report["models"][name]["by_class"][sign]["accuracy"]) for name in names]
        lines.append(f"| {sign} | {result['images']} | " + " | ".join(cells) + " |")
    lines += ["", "## Accuracy by lighting", "", "| Condition | Photos | " + " | ".join(names) + " |",
              "| --- | ---: |" + " ---: |" * len(names)]
    for condition, result in report["models"][names[0]]["by_condition"].items():
        cells = [percent(report["models"][name]["by_condition"][condition]["accuracy"]) for name in names]
        lines.append(f"| {condition} | {result['images']} | " + " | ".join(cells) + " |")
    lines += ["", "## Most common mistakes", ""]
    for name in names:
        confusions = report["models"][name]["common_confusions"][:5]
        text = ", ".join(f"{c['actual']} → {c['predicted']} ({c['count']})" for c in confusions) or "none"
        lines.append(f"- **{name}:** {text}")
    return "\n".join(lines) + "\n"


def main():
    with CLASSES_FILE.open(newline="", encoding="utf-8") as handle:
        classes = sorted(csv.DictReader(handle), key=lambda row: int(row["class_index"]))
    labels = [row["label"] for row in classes]
    rows = load_photos(labels)
    dataset = make_dataset(rows)

    report = {
        "images": len(rows),
        "shuffle_seed": SEED,
        "class_labels": labels,
        "photos_per_class": dict(Counter(row["sign_class"] for row in rows)),
        "models": {},
    }
    for name, (model_path, training_report_path) in MODELS.items():
        training_report = json.loads(training_report_path.read_text(encoding="utf-8"))
        if training_report["class_labels"] != labels:
            raise ValueError(f"{model_path.name} class order does not match {CLASSES_FILE}")
        model = tf.keras.models.load_model(model_path, compile=False)
        probabilities = model.predict(dataset, verbose=0)
        report["models"][name] = {"model_file": model_path.name} | evaluate(rows, probabilities, labels)
        overall = report["models"][name]["overall"]
        print(f"{name}: {overall['correct']}/{overall['images']} ({percent(overall['accuracy'])})")

    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(markdown(report), encoding="utf-8")
    print(f"Saved {REPORT_PATH} and {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
