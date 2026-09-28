#!/usr/bin/env python3
"""Convert the original LISA traffic-sign dataset into classifier folders."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import tensorflow as tf


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png"}
SPLITS = ("train", "validation", "test")


@dataclass(frozen=True)
class Annotation:
    row_number: int
    filename: str
    label: str
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    occluded: str
    on_another_road: str
    group_id: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Crop the 47 LISA traffic-sign classes and create deterministic "
            "train/validation/test folders for classification."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Unpacked original LISA dataset directory, or its allAnnotations.csv file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New directory to create. It must not already exist.",
    )
    parser.add_argument(
        "--expected-classes",
        type=int,
        default=47,
        help="Fail unless this many annotation labels are found (default: 47).",
    )
    parser.add_argument(
        "--minimum-crop-size",
        type=int,
        default=32,
        help="Minimum square crop side in pixels (default: 32).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=123,
        help="Seed used for deterministic group assignment (default: 123).",
    )
    parser.add_argument(
        "--no-strip",
        action="store_true",
        help=(
            "Do not delete unneeded files (negatives, tools, docs, per-folder "
            "annotation copies) from the source dataset."
        ),
    )
    return parser.parse_args()


def find_annotation_file(source: Path) -> Path:
    source = source.expanduser().resolve()
    if source.is_file():
        if source.name != "allAnnotations.csv":
            raise ValueError("--source file must be named allAnnotations.csv")
        return source
    if not source.is_dir():
        raise FileNotFoundError(f"Source does not exist: {source}")

    direct = source / "allAnnotations.csv"
    if direct.is_file():
        return direct

    matches = list(source.rglob("allAnnotations.csv"))
    if len(matches) != 1:
        raise ValueError(
            f"Expected one allAnnotations.csv below {source}, found {len(matches)}"
        )
    return matches[0]


def parse_flags(row: dict[str, str]) -> tuple[str, str]:
    if "Occluded" in row and "On another road" in row:
        return row["Occluded"].strip(), row["On another road"].strip()

    combined = row.get("Occluded,On another road", "")
    parts = [part.strip() for part in combined.split(",", maxsplit=1)]
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", ""


def clean_value(row: dict[str, str], key: str) -> str:
    value = row.get(key)
    if value is None:
        return ""
    return value.strip()


def make_group_id(row: dict[str, str], filename: str, label: str) -> str:
    """Keep repeated frames of one tracked sign in the same split."""
    normalized = filename.replace("\\", "/")
    segment = normalized.split("/", maxsplit=1)[0]
    origin_file = clean_value(row, "Origin file")
    origin_track = clean_value(row, "Origin track")

    if origin_track:
        return "|".join((label, segment, origin_file, origin_track))

    # Older mirrors sometimes omit tracking columns. Group at image level then.
    return "|".join((label, normalized))


def read_annotations(annotation_file: Path) -> list[Annotation]:
    annotations: list[Annotation] = []
    required = {
        "Filename",
        "Annotation tag",
        "Upper left corner X",
        "Upper left corner Y",
        "Lower right corner X",
        "Lower right corner Y",
    }

    with annotation_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            raise ValueError(
                "allAnnotations.csv is missing columns: " + ", ".join(sorted(missing))
            )

        for row_number, row in enumerate(reader, start=2):
            filename = clean_value(row, "Filename")
            label = clean_value(row, "Annotation tag")
            if not filename or not label:
                raise ValueError(f"Row {row_number} has an empty filename or label")

            try:
                x_min = int(clean_value(row, "Upper left corner X"))
                y_min = int(clean_value(row, "Upper left corner Y"))
                x_max = int(clean_value(row, "Lower right corner X"))
                y_max = int(clean_value(row, "Lower right corner Y"))
            except ValueError as error:
                raise ValueError(f"Row {row_number} has non-integer coordinates") from error

            if x_max < x_min or y_max < y_min:
                raise ValueError(f"Row {row_number} has an inverted bounding box")

            occluded, on_another_road = parse_flags(row)
            annotations.append(
                Annotation(
                    row_number=row_number,
                    filename=filename,
                    label=label,
                    x_min=x_min,
                    y_min=y_min,
                    x_max=x_max,
                    y_max=y_max,
                    occluded=occluded,
                    on_another_road=on_another_road,
                    group_id=make_group_id(row, filename, label),
                )
            )

    if not annotations:
        raise ValueError("No annotations were found")
    return annotations


def slugify_labels(labels: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    for label in sorted(labels, key=str.casefold):
        base = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_") or "class"
        slug = base
        if slug in used:
            suffix = hashlib.sha256(label.encode("utf-8")).hexdigest()[:8]
            slug = f"{base}_{suffix}"
        used.add(slug)
        result[label] = slug
    return result


def stable_order(seed: int, label: str, group_id: str) -> str:
    value = f"{seed}|{label}|{group_id}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def split_counts(group_count: int) -> dict[str, int]:
    """Approximate 80/10/10 while giving rare classes usable coverage."""
    if group_count == 1:
        return {"train": 1, "validation": 0, "test": 0}
    if group_count == 2:
        return {"train": 1, "validation": 1, "test": 0}

    raw = {
        "train": group_count * 0.8,
        "validation": group_count * 0.1,
        "test": group_count * 0.1,
    }
    counts = {split: max(1, math.floor(value)) for split, value in raw.items()}

    while sum(counts.values()) > group_count:
        candidates = [split for split in SPLITS if counts[split] > 1]
        split = max(candidates, key=lambda name: counts[name] - raw[name])
        counts[split] -= 1
    while sum(counts.values()) < group_count:
        split = max(SPLITS, key=lambda name: raw[name] - counts[name])
        counts[split] += 1
    return counts


def assign_splits(annotations: list[Annotation], seed: int) -> dict[tuple[str, str], str]:
    groups_by_label: dict[str, set[str]] = defaultdict(set)
    for annotation in annotations:
        groups_by_label[annotation.label].add(annotation.group_id)

    assignments: dict[tuple[str, str], str] = {}
    for label, group_ids in groups_by_label.items():
        ordered = sorted(group_ids, key=lambda group: stable_order(seed, label, group))
        counts = split_counts(len(ordered))
        start = 0
        for split in SPLITS:
            stop = start + counts[split]
            for group_id in ordered[start:stop]:
                assignments[(label, group_id)] = split
            start = stop
    return assignments


def build_image_index(root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES:
            index[path.name].append(path)
    return index


def resolve_images(
    annotations: list[Annotation], dataset_root: Path
) -> dict[str, Path]:
    index = build_image_index(dataset_root)
    resolved: dict[str, Path] = {}
    failures: list[str] = []

    for filename in sorted({item.filename for item in annotations}):
        normalized = filename.replace("\\", "/").lstrip("./")
        direct = dataset_root / normalized
        if direct.is_file():
            resolved[filename] = direct
            continue

        candidates = index.get(Path(normalized).name, [])
        suffix_matches = [
            path
            for path in candidates
            if path.relative_to(dataset_root).as_posix().endswith(normalized)
        ]
        usable = suffix_matches or candidates
        if len(usable) == 1:
            resolved[filename] = usable[0]
        else:
            failures.append(f"{filename} ({len(usable)} possible matches)")

    if failures:
        sample = "\n  ".join(failures[:10])
        raise FileNotFoundError(
            f"Could not uniquely resolve {len(failures)} source images. First entries:\n  {sample}"
        )
    return resolved


def strip_source(dataset_root: Path, keep: set[Path]) -> None:
    """Delete every file below dataset_root that is not in keep, then empty folders."""
    keep = {path.resolve() for path in keep}
    removed_files = 0
    removed_bytes = 0

    for path in sorted(dataset_root.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            if path.resolve() in keep:
                continue
            removed_bytes += path.lstat().st_size
            path.unlink()
            removed_files += 1
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()

    print(
        f"Stripped {removed_files} unneeded files "
        f"({removed_bytes / 1024**3:.2f} GB) from {dataset_root}"
    )


def square_box(
    annotation: Annotation,
    image_width: int,
    image_height: int,
    minimum: int,
) -> tuple[int, int, int, int]:
    width = annotation.x_max - annotation.x_min + 1
    height = annotation.y_max - annotation.y_min + 1
    side = min(max(width, height, minimum), image_width, image_height)
    center_x = (annotation.x_min + annotation.x_max + 1) / 2
    center_y = (annotation.y_min + annotation.y_max + 1) / 2

    left = round(center_x - side / 2)
    top = round(center_y - side / 2)
    left = min(max(left, 0), image_width - side)
    top = min(max(top, 0), image_height - side)
    return left, top, left + side, top + side


def crop_name(annotation: Annotation) -> str:
    identity = (
        f"{annotation.filename}|{annotation.x_min}|{annotation.y_min}|"
        f"{annotation.x_max}|{annotation.y_max}|{annotation.label}"
    )
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"annotation_{annotation.row_number:05d}_{suffix}.png"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prepare(args: argparse.Namespace) -> None:
    annotation_file = find_annotation_file(args.source)
    dataset_root = annotation_file.parent
    output = args.output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists; choose a new path: {output}")
    if output.is_relative_to(dataset_root):
        raise ValueError("--output must be outside the source dataset directory")
    if args.minimum_crop_size < 1:
        raise ValueError("--minimum-crop-size must be positive")

    annotations = read_annotations(annotation_file)
    labels = {item.label for item in annotations}
    if args.expected_classes and len(labels) != args.expected_classes:
        raise ValueError(
            f"Expected {args.expected_classes} classes, found {len(labels)}. "
            "Confirm that this is the original complete LISA traffic-sign dataset."
        )

    print(f"Annotations: {len(annotations)}")
    print(f"Classes: {len(labels)}")
    print("Resolving source images...")
    images = resolve_images(annotations, dataset_root)
    if not args.no_strip:
        keep = {annotation_file, dataset_root / "categories.txt", *images.values()}
        strip_source(dataset_root, keep)
    assignments = assign_splits(annotations, args.seed)
    slugs = slugify_labels(labels)

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-building-", dir=output.parent))
    manifest_rows: list[dict[str, object]] = []
    counts: Counter[tuple[str, str]] = Counter()
    current_path: Path | None = None
    current_image: tf.Tensor | None = None

    try:
        for split in SPLITS:
            for slug in slugs.values():
                (staging / split / slug).mkdir(parents=True, exist_ok=True)

        total = len(annotations)
        for position, annotation in enumerate(annotations, start=1):
            source_image = images[annotation.filename]
            if source_image != current_path:
                encoded = tf.io.read_file(str(source_image))
                current_image = tf.io.decode_image(
                    encoded, channels=3, expand_animations=False
                )
                current_path = source_image

            assert current_image is not None
            image_height = int(current_image.shape[0])
            image_width = int(current_image.shape[1])
            left, top, right, bottom = square_box(
                annotation, image_width, image_height, args.minimum_crop_size
            )
            if right <= left or bottom <= top:
                raise ValueError(f"Row {annotation.row_number} produced an empty crop")

            split = assignments[(annotation.label, annotation.group_id)]
            slug = slugs[annotation.label]
            relative_output = Path(split) / slug / crop_name(annotation)
            crop = current_image[top:bottom, left:right, :]
            tf.io.write_file(str(staging / relative_output), tf.io.encode_png(crop))
            counts[(annotation.label, split)] += 1

            manifest_rows.append(
                {
                    "output_file": relative_output.as_posix(),
                    "split": split,
                    "class_directory": slug,
                    "label": annotation.label,
                    "source_image": source_image.relative_to(dataset_root).as_posix(),
                    "source_x_min": annotation.x_min,
                    "source_y_min": annotation.y_min,
                    "source_x_max": annotation.x_max,
                    "source_y_max": annotation.y_max,
                    "crop_x_min": left,
                    "crop_y_min": top,
                    "crop_x_max_exclusive": right,
                    "crop_y_max_exclusive": bottom,
                    "occluded": annotation.occluded,
                    "on_another_road": annotation.on_another_road,
                    "group_id": annotation.group_id,
                }
            )
            if position % 500 == 0 or position == total:
                print(f"Prepared {position}/{total} crops")

        class_rows: list[dict[str, object]] = []
        for class_index, slug in enumerate(sorted(slugs.values())):
            label = next(name for name, value in slugs.items() if value == slug)
            class_rows.append(
                {
                    "class_index": class_index,
                    "class_directory": slug,
                    "label": label,
                    "train": counts[(label, "train")],
                    "validation": counts[(label, "validation")],
                    "test": counts[(label, "test")],
                    "total": sum(counts[(label, split)] for split in SPLITS),
                }
            )

        write_csv(
            staging / "manifest.csv",
            list(manifest_rows[0].keys()),
            manifest_rows,
        )
        write_csv(
            staging / "classes.csv",
            list(class_rows[0].keys()),
            class_rows,
        )

        split_totals = {
            split: sum(counts[(label, split)] for label in labels) for split in SPLITS
        }
        missing_coverage = {
            split: sorted(label for label in labels if counts[(label, split)] == 0)
            for split in ("validation", "test")
        }
        summary = {
            "source_annotation_file": str(annotation_file),
            "annotations": len(annotations),
            "unique_source_images": len(images),
            "classes": len(labels),
            "split_totals": split_totals,
            "minimum_crop_size": args.minimum_crop_size,
            "seed": args.seed,
            "classes_missing_from_validation": missing_coverage["validation"],
            "classes_missing_from_test": missing_coverage["test"],
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging)
        raise

    print(f"Output: {output}")
    print("Split totals: " + ", ".join(f"{k}={v}" for k, v in split_totals.items()))
    if any(missing_coverage.values()):
        print(
            "Warning: some rare classes lack independent tracked signs for every split. "
            "See summary.json and classes.csv."
        )


def main() -> None:
    args = parse_args()
    try:
        prepare(args)
    except (FileExistsError, FileNotFoundError, OSError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
