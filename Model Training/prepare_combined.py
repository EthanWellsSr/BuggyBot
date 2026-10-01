#!/usr/bin/env python3
"""Combine the prepared LISA and Mapillary crops without changing their splits."""

import csv
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA_ROOT = HERE / "LISA"
SOURCES = {"lisa": DATA_ROOT / "prepared", "mapillary": DATA_ROOT / "mapillary_prepared"}
OUTPUT = DATA_ROOT / "Combined"
SPLITS = ("train", "validation", "test")


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"{OUTPUT} already exists; move or remove it before rebuilding")

    source_classes = {name: read_csv(root / "classes.csv") for name, root in SOURCES.items()}
    classes = sorted(source_classes["lisa"], key=lambda row: int(row["class_index"]))
    class_ids = [(row["class_index"], row["class_directory"], row["label"]) for row in classes]
    for name, rows in source_classes.items():
        ordered = sorted(rows, key=lambda row: int(row["class_index"]))
        if [(row["class_index"], row["class_directory"], row["label"]) for row in ordered] != class_ids:
            raise ValueError(f"Class indices or labels differ in {name}")

    manifests = {name: read_csv(root / "manifest.csv") for name, root in SOURCES.items()}
    source_fields = list(dict.fromkeys(
        field for rows in manifests.values() for row in rows for field in row if field != "output_file"
    ))
    manifest_fields = ["output_file", "dataset", "source_output_file", *source_fields]
    counts = Counter()
    seen_hashes = {}
    staging = Path(tempfile.mkdtemp(prefix=".combined-", dir=DATA_ROOT))
    try:
        with (staging / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=manifest_fields)
            writer.writeheader()
            for name, root in SOURCES.items():
                for row in manifests[name]:
                    source_relative = Path(row["output_file"])
                    if source_relative.is_absolute() or ".." in source_relative.parts:
                        raise ValueError(f"Invalid source path: {source_relative}")
                    split, class_directory, filename = source_relative.parts
                    if split not in SPLITS or class_directory != row["class_directory"]:
                        raise ValueError(f"Manifest split/class mismatch: {name}/{source_relative}")
                    if class_directory not in {item[1] for item in class_ids}:
                        raise ValueError(f"Unknown class: {class_directory}")
                    source = root / source_relative
                    if not source.is_file():
                        raise FileNotFoundError(source)

                    digest = hashlib.sha256(source.read_bytes()).hexdigest()
                    previous = seen_hashes.setdefault(digest, split)
                    if previous != split:
                        raise ValueError(f"Exact PNG occurs in both {previous} and {split}: {source}")

                    output_relative = Path(split) / class_directory / f"{name}__{filename}"
                    destination = staging / output_relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists():
                        raise ValueError(f"Duplicate destination: {output_relative}")
                    shutil.copy2(source, destination)
                    combined_row = {
                        **row,
                        "output_file": output_relative.as_posix(),
                        "dataset": name,
                        "source_output_file": source_relative.as_posix(),
                        "group_id": f"{name}|{row['group_id']}",
                    }
                    writer.writerow(combined_row)
                    counts[(name, split, class_directory)] += 1

        with (staging / "classes.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["class_index", "class_directory", "label", *SPLITS, "total"])
            writer.writeheader()
            for class_id, class_directory, label in class_ids:
                split_counts = {
                    split: sum(counts[(name, split, class_directory)] for name in SOURCES)
                    for split in SPLITS
                }
                writer.writerow({
                    "class_index": class_id,
                    "class_directory": class_directory,
                    "label": label,
                    **split_counts,
                    "total": sum(split_counts.values()),
                })

        summary = {
            "sources": {name: str(root.relative_to(HERE)) for name, root in SOURCES.items()},
            "source_metadata_sha256": {
                name: {
                    filename: hashlib.sha256((root / filename).read_bytes()).hexdigest()
                    for filename in ("classes.csv", "manifest.csv")
                }
                for name, root in SOURCES.items()
            },
            "split_method": "Preserved each source's existing train, validation, and test assignment.",
            "exact_png_overlap_across_splits": 0,
            "physical_sign_overlap_across_datasets": "unknown",
            "counts": {
                name: {split: sum(counts[(name, split, class_directory)] for _, class_directory, _ in class_ids)
                       for split in SPLITS}
                for name in SOURCES
            },
            "split_totals": {
                split: sum(counts[(name, split, class_directory)] for name in SOURCES
                           for _, class_directory, _ in class_ids)
                for split in SPLITS
            },
        }
        (staging / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        staging.rename(OUTPUT)
    except Exception:
        shutil.rmtree(staging)
        raise
    print(f"Prepared {OUTPUT}")
    print(f"Crops by split: {summary['split_totals']}")
    print(f"Crops by source: {summary['counts']}")


if __name__ == "__main__":
    main()
