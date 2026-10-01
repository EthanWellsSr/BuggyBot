#!/usr/bin/env python3
"""Prepare the fully annotated Mapillary signs for the 12 LISA model classes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import os
import shutil
import tempfile
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import tensorflow as tf


HERE = Path(__file__).resolve().parent
RAW = HERE / "LISA" / "mapillary_raw"
DEFAULT_OUTPUT = HERE / "LISA" / "mapillary_prepared"
ARCHIVES = {
    "annotations": "mtsd_v2_fully_annotated_annotation.zip",
    "train.0": "mtsd_v2_fully_annotated_images.train.0.zip",
    "train.1": "mtsd_v2_fully_annotated_images.train.1.zip",
    "train.2": "mtsd_v2_fully_annotated_images.train.2.zip",
    "val": "mtsd_v2_fully_annotated_images.val.zip",
}
# Conservative US-style variants. These map to the existing LISA class labels.
LABEL_TO_CLASS = {
    "warning--added-lane-right--g1": "addedLane",
    "regulatory--keep-right--g4": "keepRight",
    "warning--traffic-merges-right--g1": "merge",
    "warning--pedestrians-crossing--g4": "pedestrianCrossing",
    "warning--school-zone--g2": "school",
    "warning--traffic-signals--g3": "signalAhead",
    "regulatory--maximum-speed-limit-25--g2": "speedLimit25",
    "regulatory--maximum-speed-limit-30--g3": "speedLimit30",
    "regulatory--maximum-speed-limit-35--g2": "speedLimit35",
    "regulatory--maximum-speed-limit-45--g3": "speedLimit45",
    "regulatory--maximum-speed-limit-65--g2": "speedLimit65",
    "regulatory--stop--g1": "stop",
}
CLASSES = sorted(set(LABEL_TO_CLASS.values()), key=str.casefold)
SPLITS = ("train", "validation", "test")
BAD_PROPERTIES = ("ambiguous", "dummy", "out-of-frame", "included")
MINIMUM_BOX_SIDE = 24
MINIMUM_CROP_SIDE = 32
VALIDATION_FRACTION = 0.12


@dataclass(frozen=True)
class Candidate:
    image_key: str
    object_key: str
    original_split: str
    label: str
    class_name: str
    bbox: dict[str, float]
    width: int
    height: int
    properties: dict[str, bool]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=RAW, help="Directory with the five original ZIPs")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="New prepared directory")
    parser.add_argument("--exclusions", type=Path, default=RAW / "exclusions.csv", help="Optional review exclusions CSV")
    parser.add_argument("--seed", type=int, default=123, help="Deterministic split seed")
    return parser.parse_args()


def read_exclusions(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not {"image_key", "object_key"}.issubset(reader.fieldnames or []):
            raise ValueError("Exclusions CSV needs image_key and object_key columns")
        rows = {(r["image_key"].strip(), r["object_key"].strip()) for r in reader}
    if any(not image or not obj for image, obj in rows):
        raise ValueError("Exclusions CSV contains an empty image_key or object_key")
    return rows


def read_candidates(annotation_zip: zipfile.ZipFile, exclusions: set[tuple[str, str]]):
    base = "mtsd_v2_fully_annotated"
    source_splits = {
        key: split
        for split in ("train", "val")
        for key in annotation_zip.read(f"{base}/splits/{split}.txt").decode().splitlines()
    }
    if len(source_splits) != 36589 + 5320:
        raise ValueError("Unexpected Mapillary train/validation split size")

    candidates: list[Candidate] = []
    filtered: Counter[str] = Counter()
    seen_exclusions: set[tuple[str, str]] = set()
    names = sorted(n for n in annotation_zip.namelist() if n.startswith(f"{base}/annotations/") and n.endswith(".json"))
    for name in names:
        image_key = Path(name).stem
        if image_key not in source_splits:
            raise ValueError(f"Annotation has no train/validation split: {image_key}")
        data = json.loads(annotation_zip.read(name))
        for obj in data["objects"]:
            label = obj["label"]
            if label not in LABEL_TO_CLASS:
                continue
            filtered["mapped_annotations"] += 1
            identity = (image_key, obj["key"])
            if identity in exclusions:
                seen_exclusions.add(identity)
                filtered["manual_exclusion"] += 1
                continue
            if data.get("ispano", False):
                filtered["panorama"] += 1
                continue
            bbox = obj["bbox"]
            if bbox["xmax"] - bbox["xmin"] < MINIMUM_BOX_SIDE or bbox["ymax"] - bbox["ymin"] < MINIMUM_BOX_SIDE:
                filtered["small_or_wrapped_box"] += 1
                continue
            if any(obj["properties"].get(flag, False) for flag in BAD_PROPERTIES):
                filtered["bad_property"] += 1
                continue
            candidates.append(Candidate(image_key, obj["key"], source_splits[image_key], label,
                                        LABEL_TO_CLASS[label], bbox, data["width"], data["height"],
                                        obj["properties"]))
    missing_exclusions = exclusions - seen_exclusions
    if missing_exclusions:
        raise ValueError(f"{len(missing_exclusions)} exclusion IDs did not match mapped annotations")
    if not candidates:
        raise ValueError("No eligible Mapillary sign crops were found")
    return candidates, source_splits, filtered


def image_archive_index(archives: dict[str, zipfile.ZipFile], source_splits: dict[str, str]):
    index: dict[str, str] = {}
    for archive_name, archive in archives.items():
        for name in archive.namelist():
            if not name.startswith("images/") or not name.endswith(".jpg"):
                continue
            key = Path(name).stem
            if key in index:
                raise ValueError(f"Duplicate image across ZIPs: {key}")
            if source_splits.get(key) != ("val" if archive_name == "val" else "train"):
                raise ValueError(f"Image is in the wrong archive: {key}")
            index[key] = archive_name
    if set(index) != set(source_splits):
        raise ValueError(f"Archive image keys differ from annotations: missing={len(set(source_splits)-set(index))}, extra={len(set(index)-set(source_splits))}")
    return index


def stable_fraction(seed: int, image_key: str) -> float:
    digest = hashlib.sha256(f"{seed}|{image_key}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def assign_splits(candidates: list[Candidate], seed: int) -> dict[str, str]:
    by_image: dict[str, set[str]] = defaultdict(set)
    source_split = {}
    for item in candidates:
        by_image[item.image_key].add(item.class_name)
        source_split[item.image_key] = item.original_split
    assigned = {
        key: "test" if source_split[key] == "val" else
        "validation" if stable_fraction(seed, key) < VALIDATION_FRACTION else "train"
        for key in by_image
    }
    # Keep every class visible in validation when the official train split allows it.
    for class_name in CLASSES:
        while sum(item.class_name == class_name and assigned[item.image_key] == "validation" for item in candidates) < 2:
            possible = [key for key, labels in by_image.items() if class_name in labels and assigned[key] == "train"]
            if len(possible) <= 1:
                break
            key = min(possible, key=lambda value: (stable_fraction(seed, value), value))
            assigned[key] = "validation"
    return assigned


def square_box(item: Candidate) -> tuple[int, int, int, int]:
    box = item.bbox
    side = min(math.ceil(max(box["xmax"] - box["xmin"], box["ymax"] - box["ymin"], MINIMUM_CROP_SIDE)), item.width, item.height)
    left = round((box["xmin"] + box["xmax"] - side) / 2)
    top = round((box["ymin"] + box["ymax"] - side) / 2)
    left = min(max(left, 0), item.width - side)
    top = min(max(top, 0), item.height - side)
    return left, top, left + side, top + side


def crop_name(item: Candidate) -> str:
    digest = hashlib.sha256(f"{item.image_key}|{item.object_key}".encode()).hexdigest()[:16]
    return f"mapillary_{digest}.png"


def write_csv(path: Path, fields: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_review_pages(output: Path, rows: list[dict], class_rows: list[dict]):
    review = output / "review"
    review.mkdir()
    style = """<style>body{font:15px system-ui;margin:2rem;background:#f8f8f8;color:#222}
    a{color:#07569b} .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
    figure{margin:0;padding:8px;background:white;border:1px solid #ddd;overflow-wrap:anywhere}
    img{display:block;width:128px;height:128px;object-fit:contain;margin:auto}
    figcaption{font-size:11px}code{user-select:all}</style>"""
    links = []
    for class_row in class_rows:
        class_name = class_row["label"]
        subset = [r for r in rows if r["label"] == class_name]
        cards = []
        for row in subset:
            src = "../" + row["output_file"]
            identity = f"{row['image_key']},{row['object_key']}"
            cards.append(f"<figure><img loading='lazy' src='{html.escape(src)}'><figcaption>"
                         f"{html.escape(row['split'])} · {html.escape(row['original_split'])}<br>"
                         f"<code>{html.escape(identity)}</code></figcaption></figure>")
        page = f"{class_row['class_directory']}.html"
        (review / page).write_text(f"<!doctype html><meta charset='utf-8'><title>{html.escape(class_name)}</title>{style}"
                                   f"<p><a href='index.html'>All classes</a></p><h1>{html.escape(class_name)} ({len(subset)})</h1>"
                                   "<p>Caption: prepared split · original Mapillary split, then image_key,object_key for exclusions.csv.</p>"
                                   f"<div class='grid'>{''.join(cards)}</div>", encoding="utf-8")
        links.append(f"<li><a href='{html.escape(page)}'>{html.escape(class_name)}</a>: {len(subset)}</li>")
    (review / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Mapillary review</title>" + style +
                                      "<h1>Mapillary candidate review</h1><p>Inspect crops before training. "
                                      "The stop label can include PARE; speed-limit labels can include truck-specific signs.</p><ul>" +
                                      "".join(links) + "</ul>", encoding="utf-8")


def prepare(args: argparse.Namespace):
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    if output.is_relative_to(source):
        raise ValueError("Output must be outside the raw ZIP directory")
    if not all((source / name).is_file() for name in ARCHIVES.values()):
        raise FileNotFoundError("The five fully annotated Mapillary ZIPs are required in --source")
    exclusions = read_exclusions(args.exclusions.expanduser().resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}-building-", dir=output.parent))
    try:
        with zipfile.ZipFile(source / ARCHIVES["annotations"]) as annotation_zip:
            candidates, source_splits, filtered = read_candidates(annotation_zip, exclusions)
        archives = {key: zipfile.ZipFile(source / name) for key, name in ARCHIVES.items() if key != "annotations"}
        try:
            index = image_archive_index(archives, source_splits)
            assigned = assign_splits(candidates, args.seed)
            for split in SPLITS:
                for class_name in CLASSES:
                    (staging / split / class_name.lower()).mkdir(parents=True)
            manifest = []
            counts: Counter[tuple[str, str]] = Counter()
            by_image: dict[str, list[Candidate]] = defaultdict(list)
            for item in candidates:
                by_image[item.image_key].append(item)
            for position, image_key in enumerate(sorted(by_image), start=1):
                archive_name = index[image_key]
                encoded = archives[archive_name].read(f"images/{image_key}.jpg")
                image = tf.io.decode_image(encoded, channels=3, expand_animations=False)
                height, width = int(image.shape[0]), int(image.shape[1])
                for item in by_image[image_key]:
                    if (width, height) != (item.width, item.height):
                        raise ValueError(f"Annotation dimensions differ from image: {image_key}")
                    left, top, right, bottom = square_box(item)
                    split = assigned[image_key]
                    relative = Path(split) / item.class_name.lower() / crop_name(item)
                    crop = image[top:bottom, left:right, :]
                    tf.io.write_file(str(staging / relative), tf.io.encode_png(crop))
                    counts[(item.class_name, split)] += 1
                    manifest.append({
                        "output_file": relative.as_posix(), "split": split,
                        "class_directory": item.class_name.lower(), "label": item.class_name,
                        "source_image": f"{ARCHIVES[archive_name]}::images/{image_key}.jpg",
                        "image_key": image_key, "object_key": item.object_key,
                        "original_split": item.original_split, "mapillary_label": item.label,
                        "source_x_min": item.bbox["xmin"], "source_y_min": item.bbox["ymin"],
                        "source_x_max": item.bbox["xmax"], "source_y_max": item.bbox["ymax"],
                        "crop_x_min": left, "crop_y_min": top,
                        "crop_x_max_exclusive": right, "crop_y_max_exclusive": bottom,
                        "occluded": item.properties.get("occluded", False),
                        "group_id": f"mapillary|{image_key}",
                    })
                if position % 500 == 0 or position == len(by_image):
                    print(f"Prepared {position}/{len(by_image)} source images", flush=True)
        finally:
            for archive in archives.values():
                archive.close()
        manifest.sort(key=lambda row: row["output_file"])
        class_rows = [{"class_index": i, "class_directory": name.lower(), "label": name,
                       **{split: counts[(name, split)] for split in SPLITS},
                       "total": sum(counts[(name, split)] for split in SPLITS)}
                      for i, name in enumerate(CLASSES)]
        write_csv(staging / "manifest.csv", list(manifest[0]), manifest)
        write_csv(staging / "classes.csv", list(class_rows[0]), class_rows)
        summary = {
            "source": "Mapillary Traffic Sign Dataset v2 fully annotated",
            "source_archives": ARCHIVES, "seed": args.seed,
            "selection": {"labels": LABEL_TO_CLASS, "minimum_box_side": MINIMUM_BOX_SIDE,
                          "minimum_crop_side": MINIMUM_CROP_SIDE, "excluded_properties": BAD_PROPERTIES,
                          "exclude_panoramas": True, "occluded_retained": True},
            "split_method": "Official Mapillary val -> test; official train -> train/validation by stable image-key hash. All signs from one source image stay together; physical sign tracks are unavailable.",
            "validation_fraction_of_original_train": VALIDATION_FRACTION,
            "filtered": dict(filtered), "exclusions": len(exclusions),
            "source_images_used": len(by_image), "crops": len(manifest), "classes": len(CLASSES),
            "split_totals": {split: sum(counts[(name, split)] for name in CLASSES) for split in SPLITS},
            "classes_missing_from_validation": [name for name in CLASSES if counts[(name, "validation")] == 0],
            "classes_missing_from_test": [name for name in CLASSES if counts[(name, "test")] == 0],
            "review_required": "Stop g1 includes non-English wording and speed-limit classes can include truck-specific signs; inspect all class galleries and add unwanted IDs to exclusions.csv before training.",
        }
        (staging / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        write_review_pages(staging, manifest, class_rows)
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging)
        raise
    print(f"Output: {output}")
    print("Split totals:", summary["split_totals"])


def main():
    args = parse_args()
    try:
        prepare(args)
    except (FileExistsError, FileNotFoundError, OSError, ValueError, zipfile.BadZipFile) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
