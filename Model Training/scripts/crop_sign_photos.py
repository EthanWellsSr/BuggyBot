#!/usr/bin/env python3
"""Crop printed sign cards out of BuggyBot camera photos.

Reads  Sign Cards/Test Images/raw/<class>/<condition>/*.jpg
Writes Sign Cards/Test Images/cropped/<class>/<condition>/*.png

The folder name gives the class, so each photo is searched for that sign's
artwork (Sign Cards/artwork) with OpenCV masked template matching:

1. Coarse: search every photo's whole frame at low resolution.
2. Prior: within one <class>/<condition> folder the camera and card barely
   move, so the median coarse box is where the sign usually is.
3. Fine: search a window around that usual place (and around the photo's own
   coarse match, if it differs) at higher resolution, over small changes in
   size, rotation, and horizontal squash.

The best match becomes a tight square crop, the same crop style used for the
LISA and Mapillary training data. Low scores are outlined in review.html.
"""

from __future__ import annotations

import argparse
import csv
import html
import statistics
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np


REPO = Path(__file__).resolve().parents[2]
TEST_IMAGES = REPO / "Sign Cards" / "Test Images"
ARTWORK = REPO / "Sign Cards" / "artwork"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}

COARSE_WIDTH = 480  # whole-frame search resolution
FINE_WIDTH = 960  # refinement resolution
COARSE_SIZES = np.geomspace(24, 300, 14)  # template widths at COARSE_WIDTH
FINE_SCALES = np.linspace(0.85, 1.15, 7)
FINE_ROTATIONS = (-8, -4, 0, 4, 8)
FINE_SQUASH = (1.0, 0.85, 0.7)  # horizontal compression for cards turned away


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=TEST_IMAGES / "raw")
    parser.add_argument("--output", type=Path, default=TEST_IMAGES / "cropped")
    parser.add_argument(
        "--max-size",
        type=int,
        default=256,
        help="Downscale crops larger than this many pixels per side (default: 256). "
        "The classifiers resize to 32x32, so more detail is not used.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Outline matches scoring below this in review.html (default: 0.5).",
    )
    return parser.parse_args()


def load_artwork() -> dict[str, np.ndarray]:
    """BGRA artwork keyed by class name; gray+alpha PNGs load as BGRA too."""
    return {
        path.stem: cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        for path in sorted(ARTWORK.glob("*.png"))
    }


def make_template(artwork: np.ndarray, width: float, rotation: float = 0, squash: float = 1.0):
    """Resize, squash, and rotate the artwork; return (BGR template, mask)."""
    height = width * artwork.shape[0] / artwork.shape[1]
    scaled = cv2.resize(
        artwork,
        (max(4, round(width * squash)), max(4, round(height))),
        interpolation=cv2.INTER_AREA,
    )
    if rotation:
        h, w = scaled.shape[:2]
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), rotation, 1.0)
        cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
        out_w, out_h = round(w * cos + h * sin), round(w * sin + h * cos)
        matrix[:, 2] += ((out_w - w) / 2, (out_h - h) / 2)
        scaled = cv2.warpAffine(scaled, matrix, (out_w, out_h))  # transparent fill
    mask = np.where(scaled[..., 3] > 127, 255, 0).astype(np.uint8)
    return scaled[..., :3], mask


def best_match(image: np.ndarray, template: np.ndarray, mask: np.ndarray):
    """Masked normalized cross-correlation; returns (score, x, y) of the best spot.

    TM_CCOEFF_NORMED subtracts each region's mean and divides by its contrast,
    so dark and bright photos of the same sign score alike (-1 to 1).
    """
    if template.shape[0] > image.shape[0] or template.shape[1] > image.shape[1]:
        return -1.0, 0, 0
    scores = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED, mask=mask)
    scores = np.nan_to_num(scores, nan=-1.0, posinf=-1.0, neginf=-1.0)
    _, score, _, (x, y) = cv2.minMaxLoc(scores)
    return float(score), x, y


def coarse_search(photo: np.ndarray, artwork: np.ndarray) -> dict[str, float]:
    """Whole-frame search; returns the box center and width in full-res pixels."""
    scale = COARSE_WIDTH / photo.shape[1]
    small = cv2.resize(photo, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    best = None
    for width in COARSE_SIZES:
        template, mask = make_template(artwork, width)
        score, x, y = best_match(small, template, mask)
        if best is None or score > best["score"]:
            h, w = mask.shape
            best = {
                "score": score,
                "center_x": (x + w / 2) / scale,
                "center_y": (y + h / 2) / scale,
                "width": width / scale,
            }
    return best


def fine_search(photo: np.ndarray, artwork: np.ndarray, guess: dict[str, float]) -> dict:
    """Refine around a guessed center and width at FINE_WIDTH."""
    scale = FINE_WIDTH / photo.shape[1]
    image = cv2.resize(photo, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    center_x, center_y = guess["center_x"] * scale, guess["center_y"] * scale
    half_w = guess["width"] * scale * 1.1
    half_h = half_w * 1.3  # speed-limit signs are taller than wide
    x0, y0 = max(0, round(center_x - half_w)), max(0, round(center_y - half_h))
    window = image[y0 : round(center_y + half_h), x0 : round(center_x + half_w)]

    def attempt(size: float, rotation: float, squash: float) -> dict:
        template, mask = make_template(artwork, guess["width"] * scale * size, rotation, squash)
        score, x, y = best_match(window, template, mask)
        rows, cols = np.nonzero(mask)
        return {
            "score": score,
            "size": size,
            "rotation": rotation,
            "squash": squash,
            "box": (
                (x0 + x + cols.min()) / scale,
                (y0 + y + rows.min()) / scale,
                (x0 + x + cols.max() + 1) / scale,
                (y0 + y + rows.max() + 1) / scale,
            ),
        }

    # Size and rotation first, then squash at the best of those.
    best = max(
        (attempt(size, rotation, 1.0) for size in FINE_SCALES for rotation in FINE_ROTATIONS),
        key=lambda result: result["score"],
    )
    for squash in FINE_SQUASH[1:]:
        result = attempt(best["size"], best["rotation"], squash)
        if result["score"] > best["score"]:
            best = result
    return best


def square_crop(photo: np.ndarray, box: tuple[float, float, float, float]):
    """Square crop around the sign box, shifted to stay inside the photo."""
    height, width = photo.shape[:2]
    x_min, y_min, x_max, y_max = box
    side = min(round(max(x_max - x_min, y_max - y_min)), width, height)
    left = min(max(round((x_min + x_max - side) / 2), 0), width - side)
    top = min(max(round((y_min + y_max - side) / 2), 0), height - side)
    return photo[top : top + side, left : left + side], (left, top, left + side, top + side)


def write_review(path: Path, rows: list[dict], threshold: float) -> None:
    figures = []
    for row in sorted(rows, key=lambda r: (float(r["score"]), r["output_file"])):
        flag = ' class="flag"' if float(row["score"]) < threshold else ""
        name = html.escape(row["output_file"])
        figures.append(
            f'<figure{flag}><img src="{name}" loading="lazy">'
            f'<figcaption>{name}<br>score {float(row["score"]):.2f}</figcaption></figure>'
        )
    flagged = sum(float(r["score"]) < threshold for r in rows)
    path.write_text(
        "<!doctype html><meta charset=utf-8><title>Sign crop review</title>"
        "<style>body{font:13px sans-serif;margin:16px}"
        "figure{display:inline-block;margin:4px;width:150px;vertical-align:top}"
        "img{width:150px;height:150px;object-fit:contain;background:#eee}"
        "figure.flag{outline:3px solid #d00}</style>"
        f"<h1>Sign crop review</h1><p>{len(rows)} crops, lowest score first; "
        f"{flagged} below {threshold} outlined in red.</p>" + "".join(figures),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    artwork = load_artwork()
    folders = defaultdict(list)
    for path in sorted(args.raw.rglob("*")):
        if path.suffix.lower() in IMAGE_SUFFIXES:
            folders[path.parent].append(path)
    if not folders:
        raise SystemExit(f"No photos found under {args.raw}")

    rows = []
    for folder, photos in folders.items():
        sign_class = folder.relative_to(args.raw).parts[0]
        if sign_class not in artwork:
            raise SystemExit(
                f"Folder '{sign_class}' is not a class name. Use one of: {', '.join(artwork)}"
            )

        images = [cv2.imread(str(path)) for path in photos]
        coarse = [coarse_search(image, artwork[sign_class]) for image in images]

        # The usual place: median of the confident coarse matches in this folder.
        confident = [c for c in coarse if c["score"] >= args.threshold] or coarse
        prior = {
            key: statistics.median(c[key] for c in confident)
            for key in ("center_x", "center_y", "width")
        }

        for path, image, own in zip(photos, images, coarse):
            guesses = [prior]
            moved = max(
                abs(own["center_x"] - prior["center_x"]),
                abs(own["center_y"] - prior["center_y"]),
            )
            if moved > prior["width"] / 3:
                guesses.append(own)  # the card may have moved in this photo
            best = max(
                (fine_search(image, artwork[sign_class], guess) for guess in guesses),
                key=lambda result: result["score"],
            )

            crop, (left, top, right, bottom) = square_crop(image, best["box"])
            if crop.shape[0] > args.max_size:
                crop = cv2.resize(crop, (args.max_size, args.max_size), interpolation=cv2.INTER_AREA)
            relative = path.relative_to(args.raw).with_suffix(".png")
            output = args.output / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output), crop)

            rows.append(
                {
                    "output_file": relative.as_posix(),
                    "source_file": path.relative_to(args.raw).as_posix(),
                    "sign_class": sign_class,
                    "condition": relative.parts[1] if len(relative.parts) > 2 else "",
                    "score": f"{best['score']:.4f}",
                    "crop_x_min": left,
                    "crop_y_min": top,
                    "crop_x_max_exclusive": right,
                    "crop_y_max_exclusive": bottom,
                    "rotation_degrees": best["rotation"],
                    "horizontal_squash": best["squash"],
                }
            )
        scores = [float(row["score"]) for row in rows[-len(photos) :]]
        print(f"{folder.relative_to(args.raw)}: {len(photos)} crops, scores {min(scores):.2f}-{max(scores):.2f}")

    with (args.output / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_review(args.output / "review.html", rows, args.threshold)
    flagged = sum(float(row["score"]) < args.threshold for row in rows)
    print(f"Wrote {len(rows)} crops to {args.output}; {flagged} below {args.threshold}")


if __name__ == "__main__":
    main()
