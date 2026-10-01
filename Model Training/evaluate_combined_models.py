"""Compare the three 12-class models on the same combined held-out test crops."""

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import tensorflow as tf


HERE = Path(__file__).resolve().parent
DATA_ROOT = HERE / "LISA" / "Combined"
REPORT_PATH = HERE / "combined_model_comparison_report.json"
SUMMARY_PATH = HERE / "combined_model_comparison.md"
MODEL_FILES = {
    "lisa": HERE / "lisa_model_v1.keras",
    "mapillary": HERE / "mapillary_model.keras",
    "combined": HERE / "combined_model.keras",
}
TRAINING_REPORTS = {
    "lisa": HERE / "lisa_training_report.json",
    "mapillary": HERE / "mapillary_training_report.json",
    "combined": HERE / "combined_training_report.json",
}
BATCH_SIZE = 64


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_samples(class_ids):
    rows = sorted(
        (row for row in read_csv(DATA_ROOT / "manifest.csv") if row["split"] == "test"),
        key=lambda row: row["output_file"],
    )
    if len(rows) != 1016:
        raise ValueError(f"Expected 1,016 combined test crops; found {len(rows)}")
    for row in rows:
        path = DATA_ROOT / row["output_file"]
        if not path.is_file():
            raise FileNotFoundError(path)
        if row["dataset"] not in ("lisa", "mapillary"):
            raise ValueError(f"Unexpected dataset for {path}: {row['dataset']}")
        if row["class_directory"] not in class_ids:
            raise ValueError(f"Unexpected class for {path}: {row['class_directory']}")
    return rows


def make_dataset(rows, class_ids):
    paths = [str(DATA_ROOT / row["output_file"]) for row in rows]
    actual = np.asarray([class_ids[row["class_directory"]] for row in rows], dtype=np.int64)

    def load_image(path):
        image = tf.io.decode_png(tf.io.read_file(path), channels=3)
        return tf.image.resize(image, (32, 32))

    images = tf.data.Dataset.from_tensor_slices(paths)
    images = images.map(load_image, num_parallel_calls=tf.data.AUTOTUNE)
    return images.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE), actual


def metrics(actual, probabilities, labels):
    count = len(labels)
    predictions = probabilities.argmax(axis=1)
    correct = predictions == actual
    top_ids = np.argsort(probabilities, axis=1)[:, -min(3, count):]
    top_correct = np.any(top_ids == actual[:, None], axis=1)
    confusion = np.zeros((count, count), dtype=int)
    np.add.at(confusion, (actual, predictions), 1)
    per_class = {}
    for class_id, label in enumerate(labels):
        support = int(confusion[class_id].sum())
        true_positive = int(confusion[class_id, class_id])
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
    confusions = [
        {"actual": labels[row], "predicted": labels[column], "count": int(confusion[row, column])}
        for row in range(count) for column in range(count)
        if row != column and confusion[row, column]
    ]
    confusions.sort(key=lambda item: item["count"], reverse=True)
    return {
        "images": len(actual),
        "correct": int(correct.sum()),
        "incorrect": int((~correct).sum()),
        "top1_accuracy": float(correct.mean()),
        "top3_accuracy": float(top_correct.mean()),
        "macro_precision": float(np.mean([row["precision"] for row in per_class.values()])),
        "macro_recall": float(np.mean([row["recall"] for row in per_class.values()])),
        "macro_f1": float(np.mean([row["f1"] for row in per_class.values()])),
        "per_class": per_class,
        "confusion_matrix": confusion.tolist(),
        "common_confusions": confusions,
    }


def mistakes(rows, actual, probabilities, labels):
    predictions = probabilities.argmax(axis=1)
    errors = []
    for index, row in enumerate(rows):
        if actual[index] == predictions[index]:
            continue
        top_ids = np.argsort(probabilities[index])[-3:][::-1]
        errors.append({
            "image": row["output_file"],
            "dataset": row["dataset"],
            "source_image": row["source_image"],
            "group_id": row["group_id"],
            "actual": labels[int(actual[index])],
            "predicted": labels[int(predictions[index])],
            "predicted_probability": float(probabilities[index, predictions[index]]),
            "actual_probability": float(probabilities[index, actual[index]]),
            "top_predictions": [
                {"label": labels[int(candidate)], "probability": float(probabilities[index, candidate])}
                for candidate in top_ids
            ],
        })
    errors.sort(key=lambda row: row["predicted_probability"], reverse=True)
    return errors


def percent(value):
    return f"{100 * value:.2f}%"


def markdown(report):
    labels = report["class_labels"]
    results = report["models"]
    lines = [
        "# Three-model comparison on the combined test set", "",
        "All three saved models were evaluated on the same 1,016 held-out crops",
        "(584 LISA and 432 Mapillary). Per-sign accuracy below means recall:",
        "correct predictions divided by test examples of that sign.", "",
        "| Model | Correct / 1,016 | Top-1 | Top-3 | Macro F1 | LISA top-1 | Mapillary top-1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, result in results.items():
        overall = result["overall"]
        lines.append(
            f"| {name} | {overall['correct']} / {overall['images']} | "
            f"{percent(overall['top1_accuracy'])} | {percent(overall['top3_accuracy'])} | "
            f"{percent(overall['macro_f1'])} | "
            f"{percent(result['by_source']['lisa']['top1_accuracy'])} | "
            f"{percent(result['by_source']['mapillary']['top1_accuracy'])} |"
        )
    lines += ["", "## Accuracy by sign", "", "| Sign | Test crops | LISA model | Mapillary model | Combined model |", "| --- | ---: | ---: | ---: | ---: |"]
    for label in labels:
        support = results["combined"]["overall"]["per_class"][label]["support"]
        scores = [percent(results[name]["overall"]["per_class"][label]["recall"])
                  for name in MODEL_FILES]
        lines.append(f"| {label} | {support} | {' | '.join(scores)} |")
    lines += [
        "", "The [JSON report](combined_model_comparison_report.json) also contains",
        "per-source per-class metrics, confusion matrices, individual errors,",
        "and paired differences on identical images.", "",
        "The combined test set preserves each source's original split. Exact PNG",
        "duplicates across splits were checked during preparation. Physical sign",
        "overlap across Mapillary images or between datasets remains unknown.",
        "These results measure cropped road-scene signs, not the camera and",
        "detection pipeline on BuggyBot.", "",
    ]
    return "\n".join(lines)


def main():
    classes = sorted(read_csv(DATA_ROOT / "classes.csv"), key=lambda row: int(row["class_index"]))
    labels = [row["label"] for row in classes]
    class_ids = {row["class_directory"]: index for index, row in enumerate(classes)}
    if [int(row["class_index"]) for row in classes] != list(range(len(classes))):
        raise ValueError("Combined class indices are not consecutive from zero")
    rows = load_samples(class_ids)
    dataset, actual = make_dataset(rows, class_ids)
    if len(rows) != 1016 or sum(row["dataset"] == "lisa" for row in rows) != 584:
        raise ValueError("Combined test source counts changed")

    report = {
        "evaluation_split": "LISA/Combined/test",
        "class_labels": labels,
        "test_images": len(rows),
        "dataset_metadata_sha256": {
            filename: sha256(DATA_ROOT / filename)
            for filename in ("classes.csv", "manifest.csv", "summary.json")
        },
        "models": {},
    }
    predictions = {}
    for name, model_path in MODEL_FILES.items():
        training_report = json.loads(TRAINING_REPORTS[name].read_text(encoding="utf-8"))
        if training_report["class_labels"] != labels:
            raise ValueError(f"Class order in {TRAINING_REPORTS[name]} does not match combined data")
        model = tf.keras.models.load_model(model_path, compile=False)
        if model.output_shape[-1] != len(labels):
            raise ValueError(f"{model_path} output size does not match classes")
        probabilities = model.predict(dataset, verbose=0)
        if probabilities.shape != (len(rows), len(labels)):
            raise ValueError(f"Unexpected prediction shape from {model_path}: {probabilities.shape}")
        predictions[name] = probabilities.argmax(axis=1)
        source_indices = {
            source: np.asarray([index for index, row in enumerate(rows) if row["dataset"] == source])
            for source in ("lisa", "mapillary")
        }
        result = {
            "model_file": model_path.name,
            "model_sha256": sha256(model_path),
            "training_report_file": TRAINING_REPORTS[name].name,
            "overall": metrics(actual, probabilities, labels),
            "by_source": {
                source: metrics(actual[indices], probabilities[indices], labels)
                for source, indices in source_indices.items()
            },
            "errors": mistakes(rows, actual, probabilities, labels),
        }
        historical = training_report["test"]["top1_accuracy"]
        matching_source = name if name != "combined" else None
        if matching_source:
            measured = result["by_source"][matching_source]["top1_accuracy"]
            if abs(measured - historical) > 1e-9:
                raise ValueError(f"{name} test score differs from its saved training report")
        else:
            measured = result["overall"]["top1_accuracy"]
            if abs(measured - historical) > 1e-9:
                raise ValueError("Combined test score differs from its saved training report")
        report["models"][name] = result
        print(f"{name}: {result['overall']['correct']}/{len(rows)} "
              f"({percent(result['overall']['top1_accuracy'])}), "
              f"macro F1 {percent(result['overall']['macro_f1'])}")
        del model

    pairwise = {}
    for first, second in (("lisa", "mapillary"), ("lisa", "combined"), ("mapillary", "combined")):
        first_correct = predictions[first] == actual
        second_correct = predictions[second] == actual
        pairwise[f"{first}_vs_{second}"] = {
            "both_correct": int(np.sum(first_correct & second_correct)),
            "first_only_correct": int(np.sum(first_correct & ~second_correct)),
            "second_only_correct": int(np.sum(~first_correct & second_correct)),
            "both_wrong": int(np.sum(~first_correct & ~second_correct)),
            "different_predictions": int(np.sum(predictions[first] != predictions[second])),
        }
    report["pairwise"] = pairwise
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(markdown(report), encoding="utf-8")
    print(f"Saved {REPORT_PATH} and {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
