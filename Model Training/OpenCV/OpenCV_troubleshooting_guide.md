# OpenCV Sign Demo Troubleshooting Guide

Lessons learned while bringing up `pi_sign_detection_demo.py` on BuggyBot
(October 2026). Read this before changing the demo's detection logic, its
thresholds, or how it is run and viewed. Every number below was measured on
real BuggyBot camera frames or on the cropped test photos in
`Sign Cards/Test Images/cropped/`; none are guesses.

## Contents

1. [How the pipeline works](#1-how-the-pipeline-works)
2. [Running and viewing the demo](#2-running-and-viewing-the-demo)
3. [Symptom → cause → fix table](#3-symptom--cause--fix-table)
4. [The root problem: a closed-set classifier](#4-the-root-problem-a-closed-set-classifier)
5. [Detection filters, one by one](#5-detection-filters-one-by-one)
6. [Debugging workflow: reproduce errors offline](#6-debugging-workflow-reproduce-errors-offline)
7. [Results history](#7-results-history)
8. [Known remaining issues](#8-known-remaining-issues)
9. [Pitfalls that cost us time](#9-pitfalls-that-cost-us-time)
10. [Rules for future changes](#10-rules-for-future-changes)

---

## 1. How the pipeline works

Every camera frame (1280×720 by default) goes through these stages, in order:

```
Pi Camera frame
  │
  ├─ 1. make_candidates()   OpenCV proposes up to 8 sign-like boxes
  ├─ 2. crop_square()       each box → square crop with 12% margin
  ├─ 3. classify()          LiteRT model → (label, confidence) for each crop
  ├─ 4. confidence ≥ 0.85   --threshold
  ├─ 5. shape_matches()     crop's color region must have the label's shape
  ├─ 6. contains() filter   drop matches nested inside another match
  ├─ 7. confirmation        same top label on 3 consecutive frames (--confirm-frames)
  └─ 8. output              LCD text + backlight color, DETECTED line, saved PNGs
```

**Stage 1 (`make_candidates`)** is heuristic, not an object detector. It
downscales to 640 px wide and finds contours in three masks:

| Mask | What it catches |
|---|---|
| `combined` = saturation OR edges | Colored signs with strong outlines |
| `edge` (Canny) | White signs (speed limit, keepRight) |
| `sat` (saturation alone) | Colored signs whose outline merges with a holder stick in the other masks |

Contours are kept if they are sign-sized (0.06%–55% of the frame), at least
18 px, roughly square (aspect 0.65–1.5), not touching the frame edge, and at
least 18% filled. Overlapping proposals of similar size are deduplicated.

**Stage 3 (`classify`)** matches `Hardware/scripts/buggybot_integration.py`
exactly: BGR → RGB, resize to 32×32, float32 0–255 (the model rescales
internally). The model is `Model Training/models/combined_model.tflite` with
12 classes (`combined_model_labels.txt`).

**Stage 7 (confirmation)** is a state machine. `SEARCHING` runs detection every
frame. When one label wins N frames in a row, the demo switches to
`DISPLAYING`, writes the LCD once, and skips detection for `--display-seconds`
(3 s). Any different label, or no match, resets the count.

---

## 2. Running and viewing the demo

### Command

From the repository root on BuggyBot:

```bash
~/buggybot-venv/bin/python "Model Training/OpenCV/pi_sign_detection_demo.py"
```

- **Use the venv's Python.** `~/buggybot-venv` (created by `Hardware/setup.sh`)
  has LiteRT (`ai-edge-litert`). System Python does not.
- **Quote the path.** `Model Training` has a space.
- The script finds the model relative to its own location, so it runs from any
  working directory.

### Defaults (no flags needed)

| Flag | Default | Meaning |
|---|---|---|
| `--stream PORT` | 8000 | MJPEG stream; `--stream 0` disables |
| `--lcd / --no-lcd` | on | Waveshare RGB1602 output |
| `--confirm-frames` | 3 | Consecutive agreeing frames before output |
| `--threshold` | 0.85 | Minimum classifier confidence |
| `--display-seconds` | 3.0 | LCD hold time after a detection |
| `--save-every` | 2.0 | Seconds between timed frame saves (0 disables) |
| `--output` | `~/buggybot_sign_demo` | Where frames are saved |
| `--width/--height` | 1280/720 | Camera resolution |
| `--seconds` | 0 | Auto-stop after N seconds; 0 = Ctrl+C |

### Viewing the camera: use the HTTP stream

BuggyBot runs **Raspberry Pi OS Lite (Debian 13 "trixie"), headless, with no
desktop.** `cv2.imshow` windows and VNC cannot work on the Pi itself.

Open **`http://buggybot.local:8000`** in a browser on any machine on the same
network. You see the annotated frames (boxes, labels, state).

How it works (`FrameStream` class):

- MJPEG = a series of JPEGs sent in one never-ending HTTP response
  (`multipart/x-mixed-replace`). Browsers swap in each image as it arrives.
  Standard library only (`http.server`); no extra dependencies.
- Each frame is JPEG-encoded once (quality 70, roughly 50 KB at 720p).
- The server runs in its own daemon thread, so detection is never blocked.
  The main loop publishes the newest frame and notifies waiting clients. A
  slow viewer skips frames instead of building up lag.
- Several viewers can watch at once. Ctrl+C stops everything.

**Do not go back to X11 forwarding** (`ssh -Y` + XQuartz). We tried it: it sends
uncompressed frames over Wi-Fi and was unusably slow. XQuartz was removed from
the dev `setup.sh` for this reason.

### LCD behavior

| State | Text | Backlight |
|---|---|---|
| Searching | `SEARCHING...` / `NO SIGN FOUND` | Green |
| Stop detected | label / `Confidence NN%` | Red (255, 0, 0) |
| Yellow sign detected (school, pedestrianCrossing, merge, addedLane, signalAhead) | label / confidence | Amber (255, 150, 0) |
| White sign detected (speed limits, keepRight) | label / confidence | White |
| Script exits | `BUGGYBOT` / `DEMO COMPLETE` | unchanged |

Amber is used instead of pure yellow (255, 255, 0), which tends to look green
on RGB backlights. Colors come from `LCD_COLORS`, keyed by each sign's color in
`SIGN_SHAPES`, so there is one place to change them.

**The LCD keeps its last text after a script exits.** If it shows
`SEARCHING...` but never updates, check that the current run actually has the
LCD enabled. A stale message from an earlier run looks identical. To test the
hardware alone:

```bash
~/buggybot-venv/bin/python -c "import sys; sys.path.insert(0,'/home/buggybot/LCD1602-RGB-Module-demo/Raspberry'); import RGB1602; l=RGB1602.RGB1602(16,2); l.setRGB(0,255,0); l.clear(); l.printout('LCD TEST')"
```

---

## 3. Symptom → cause → fix table

| Symptom | Root cause | Fix (in the script now) |
|---|---|---|
| Can't see the camera; `ssh -Y` preview unusable | Headless OS; X11 sends uncompressed frames | MJPEG stream on port 8000 |
| `ssh` hangs at `Connecting to … port 22` | Typo in the `.local` name; mDNS waits for a timeout instead of failing | Check spelling (`buggybot.local`), or use the IP |
| LCD stuck on `SEARCHING...` | LCD wasn't enabled on that run (stale text) | LCD on by default |
| Pinkish shirt / skin labeled **stop** | Classifier has no "not a sign" class; loose color mask | Tight red hue/saturation range (§5.2) |
| Ear / nose labeled **stop** | Skin passed the red mask and the octagon corner count | Solidity ≥ 0.9 for stop (§5.3) |
| Round red objects (signalAhead's light) pass as stop | Circles approximate to 8 corners at 3% tolerance | 1% tolerance and 7–9 corners (§5.3) |
| **addedLane → merge** | Only single-arrow fragments were proposed; the holder stick merged with the sign's outline | `sat` mask as a proposal source + nested-match filter (§5.5) + diamond fill cap (§5.4) |
| **speed limit → keepRight**, one frame, then correct | Blurred or partial crop as the card enters view | Multi-frame confirmation (§5.6) |
| **speed limit → keepRight**, repeatedly | Crop of one letter or digit (sign partly off-frame or blurred), or of background | Inner ink-shape count (§5.7) |
| Motion-blurred signs misread (signalAhead/pedestrianCrossing → merge, 45 → 25) | Model was never trained on blur | `--confirm-frames 3` (§5.6) |
| Couldn't tell what caused a bad LCD output | Timed saves every 2 s rarely coincide with detections | Save frame + crop on every `DETECTED` (§6) |

---

## 4. The root problem: a closed-set classifier

**Read this before trying to "fix OpenCV".** Most false positives were not
OpenCV bugs.

- The model was trained only on the 12 sign classes. It has **no background /
  "not a sign" class.**
- Softmax outputs always sum to 100%, so for *any* input the model reports the
  sign it looks most like, often at 99–100% confidence. A pink shirt → stop at
  100% is normal behavior for this model. In ML terms, the shirt is an
  *out-of-distribution* input.
- **Confidence is not a detection score.** 100% means "stop is the best of
  these 12 options," not "this is a stop sign."
- The model was trained on upright, sharp, whole signs (LISA / Mapillary, plus
  hand-cropped test photos). It has never seen motion blur, partial signs, or
  close-up skin.

So the demo surrounds the classifier with filters (§5) that reject inputs which
can't be the predicted sign. **These filters treat symptoms.** The real fix is
retraining with BuggyBot's own crops plus a background class (§8).

---

## 5. Detection filters, one by one

All shape and color logic lives in `color_mask()` and `shape_matches()`.
`SIGN_SHAPES` maps each class to `(color, shape)`:

| Classes | Color mask | Shape |
|---|---|---|
| stop | red | octagon |
| school | yellow | pentagon |
| pedestrianCrossing, addedLane, merge, signalAhead | yellow | diamond |
| keepRight, speedLimit25/30/35/45/65 | white | rectangle |

Note: our pedestrianCrossing card is a **diamond**. It was first mislabeled
pentagon; check the physical card artwork (`Sign Cards/artwork/`) before
assigning shapes.

### 5.1 General shape check

For a crop and its predicted label:

1. Build the class's color mask (HSV), then close it with a 5×5 kernel.
2. Take the largest external contour (`region`) and its **convex hull** (a
   rubber band around it). The hull ignores letters and symbols cut into the
   mask, such as "STOP" or arrows.
3. Reject if the hull covers less than 20% of the crop.
4. Compute:
   - **extent** = hull area / bounding-box area (1.0 = rectangle, ~0.5 = upright diamond)
   - **corners** = vertex count of `approxPolyDP(hull, ε × perimeter)`

| Shape | Rule |
|---|---|
| octagon | ε = 1%, 7–9 corners, extent ≥ 0.7, solidity ≥ 0.9 |
| diamond | hull ≤ 70% of crop, then the pentagon rule |
| pentagon | ε = 3%, 4–6 corners, 0.4 ≤ extent ≤ 0.9 |
| rectangle | ε = 3%, exactly 4 corners, extent ≥ 0.8, ≥ 2 inner ink shapes (§5.7) |

Diamond and pentagon share a 4–6 corner range on purpose: a diamond clipped
at the crop edge gains a corner. So the shape check **cannot separate
diamonds from pentagons, or one diamond sign from another**
(merge vs addedLane vs signalAhead vs pedestrianCrossing). That separation is
the classifier's job.

### 5.2 Color masks (HSV, OpenCV scale: H 0–179, S/V 0–255)

| Color | Range | Why |
|---|---|---|
| red | H 0–2 or 165–179, S ≥ 100, V ≥ 25 | Red wraps around 0/179. See measurements below. |
| yellow | H 15–55, S ≥ 80, V ≥ 40 | Upper bound 55 includes the fluorescent yellow-green school sign; V ≥ 40 keeps dim photos |
| white | S ≤ 70, V ≥ Otsu threshold of the crop | Otsu adapts the brightness cutoff to each crop's lighting |

**Red measurements that set the range:**

| Source | Hue (median) | Saturation (median) |
|---|---|---|
| Printed stop card | 176 (magenta side of red) | ~150 |
| Pinkish shirt / skin, first run | 3 (orange side of red) | ~97 |

Printers reproduce stop red as a pinkish red, so the card sits on the
magenta side. Skin sits on the orange side and is duller. The original range
(H 0–10 / 160–179, S ≥ 60) let skin fill about 50% of a crop; the tight range
cuts it to about 10%, below the 20% minimum.

**Hue alone was not enough.** In a later run, under different lighting, an
ear measured H ≈ 1 and S ≈ 135, inside the tight range. That's what led to
solidity (§5.3). Lighting moves skin hue around, so don't rely on hue by
itself.

### 5.3 Stop sign: octagon, corners, and solidity

**Corner tolerance (ε).** At ε = 3%, circles and ellipses also simplified to 8
corners and passed as octagons. At ε = 1%:

| Shape | Corners at 1% |
|---|---|
| Real stop cards (test set and live) | 8 (one test crop gave 10) |
| Ellipse / circle | 14–15 |
| signalAhead's round red light | 10 → rejected by the 7–9 range |

**Solidity** = region area / hull area. It measures how concave the red
region is.

| Source | Solidity |
|---|---|
| Live stop cards | 0.98–0.99 |
| Test stop crops | 0.98–0.99 (one dim crop: 0.80) |
| Ear (11 live crops) | 0.59–0.80 |
| Nose | 0.80 |

A printed octagon is one solid red shape. Skin is shaded and folded, so its
red patches are lumpy. The rule is solidity ≥ 0.9. **Cost:** one very dim test
crop (`stop/no_light/stop_001.png`) now fails, so a stop sign in very dim light
may be missed.

### 5.4 Diamond fill cap

A whole diamond fills about half of its square crop. A crop taken from
*inside* a diamond sign is yellow edge to edge.

| Source | Yellow hull area / crop area |
|---|---|
| Diamond test crops (hand-cropped tight) | 0.53–0.63 |
| Live whole-diamond crops | ≤ 0.57 |
| Live addedLane arrow fragments (classified merge) | 0.80–0.90 |
| School pentagon test crops (not capped) | 0.77–0.78 |

The rule is: reject a diamond match if its hull area is more than 70% of the
crop. This caught 3 of 5 wrong LCD outputs in that run, with no correct
detections lost. **Risk:** a diamond held at about 45° looks like a square and
fills more of its crop. Tilted cards in testing measured 0.57, which is fine.

### 5.5 Fragments: whole-sign proposals and the nested-match filter

**The addedLane → merge failure** happened because OpenCV never proposed the
whole addedLane diamond:

- The wooden holder stick's edges joined onto the sign's outline in the
  `combined` and `edge` masks. The joined shape was too tall (aspect check) or
  ran off the bottom of the frame (edge check), so it was rejected.
- Only the yellow pieces between the arrows were left. A crop of one arrow on
  yellow looks like merge.

Fixes:

1. **`sat` mask as its own proposal source.** Color alone outlines the yellow
   diamond cleanly, without the stick. On the failing frame it gave a clean
   box with aspect 1.04.
2. **Nested-match filter (`contains()`).** If one passing match's box lies
   entirely inside another's, the inner one (the fragment) is dropped. Before
   this, the script picked the highest-confidence match, which could be the
   fragment.

**Still possible:** if the stick is saturated enough to merge with the sign
even in the `sat` mask, no whole-sign box exists for that frame. One frame
measured aspect 0.70, touching the frame bottom. Confirmation (§5.6) and the
fill cap (§5.4) cover most of these cases.

### 5.6 Multi-frame confirmation (`--confirm-frames`, default 3)

A label must be the top match on N consecutive frames before it reaches the
LCD.

- **What it filters:** errors that last only a frame or two, like the blurred
  or partial crop as a card moves into view, motion blur while it's moving, and
  speed limit → keepRight on the first frame.
- **What it cannot filter:** errors the model makes the same way every frame,
  such as a stable fragment crop or a consistent misclassification. Those need
  shape filters or retraining.
- **Why not "slow the camera down":** blur comes from motion *during* each
  frame's exposure. A slower frame rate still captures the blurred frame.
  Requiring agreement across frames is what helps.
- **N = 2** still let through 3 motion-blur errors in 36 detections.
  **N = 3** gave 32 of 32 correct, with no noticeable delay. Higher N filters
  more errors at the cost of a slower response.

### 5.7 White-sign fragments: inner ink-shape count

In a later run, 18 of 21 keepRight LCD outputs were wrong. The crops were one
letter or digit of a speed-limit sign ("M", "2", "LI"), usually with the sign
partly off-frame or blurred, or background (wall, window). A single dark glyph
on white looks most like keepRight's black arrow. The white mask also takes in
the wall, so the rectangle check passed them (§8 explains why fill fraction
can't separate them).

A whole white sign has **at least two ink shapes lying fully inside the
crop**: keepRight has its bullet and arrow, and speed limits have their
letters and digits. A fragment has one glyph, often cut by the crop edge, or
none. `inner_ink_shapes()` counts dark regions (V below the crop's Otsu
split, at least 0.5% of the crop) that don't touch the crop edge. White
rectangles need 2 or more.

| Source | Inner ink shapes |
|---|---|
| Committed white-sign test crops (132) | ≥ 3, all pass |
| Live whole keepRight / speed-limit crops | 2–9, all pass |
| Live keepRight fragments and background | 14 of 18 rejected (0–1) |

**Still passes:** fragments with two glyphs ("LI") and textured background.
Confirmation (§5.6) has to catch those.

---

## 6. Debugging workflow: reproduce errors offline

This workflow found every fix above. **Measure on real frames before changing
thresholds.**

### 6.1 What the demo saves (in `~/buggybot_sign_demo/`)

| File | When | Use |
|---|---|---|
| `frame_NNNNNN.jpg` | Every `--save-every` seconds | Annotated, so boxes appear only if a detection happened on that exact frame (rare) |
| `detect_NNNNNN_<label>_frame.png` | Every `DETECTED` | Unannotated frame, for re-running the whole pipeline |
| `detect_NNNNNN_<label>_crop.png` | Every `DETECTED` | The exact crop the model classified |

Detection files are **PNG (lossless)** and copied **before overlays are
drawn**. Re-classifying them reproduces the Pi's output exactly: in every run
we checked, all re-classifications matched the Pi's labels.

**Timed frames are not enough.** They're a 2-second sample and usually miss
the bad detection. Always analyze the `detect_*` files.

### 6.2 Copying files to the Mac

```bash
mkdir -p ~/Desktop/BuggyBot/scratch_frames
```

```bash
scp "buggybot@buggybot.local:~/buggybot_sign_demo/*" ~/Desktop/BuggyBot/scratch_frames/
```

- Use `*`, **not `*.jpg`**, or the `detect_*.png` files are left behind.
- `scratch_frames/` is in `.gitignore`. Clear it between runs so runs don't mix.
- Clear the Pi folder between runs too:
  `rm -r ~/buggybot_sign_demo` (the script recreates it).

### 6.3 Running the model on a Mac

The Mac's system Python had no working TFLite runtime (TensorFlow import
crashed with a mutex error). Use a throwaway venv outside the repo:

```bash
python3 -m venv /tmp/litert-venv && /tmp/litert-venv/bin/pip install ai-edge-litert opencv-python-headless numpy
```

(Installing dependencies needs the user's approval under `AGENTS.md`.)
Running inference is not training. It doesn't change the model.

### 6.4 Analysis recipes

Import the demo's own functions so the analysis uses exactly the Pi's logic:

```python
import sys, glob, cv2
sys.path.insert(0, 'Model Training/OpenCV')
import pi_sign_detection_demo as d

it = d.load_interpreter(d.MODEL_PATH)
labels = d.LABELS_PATH.read_text().split()

# 1. Re-classify every LCD output
for f in sorted(glob.glob('scratch_frames/detect_*_crop.png')):
    print(f, d.classify(it, labels, cv2.imread(f)))

# 2. Re-run the full pipeline on a frame
im = cv2.imread('scratch_frames/detect_001328_merge_frame.png')
for box in d.make_candidates(im, 8):
    crop = d.crop_square(im, box)
    label, conf = d.classify(it, labels, crop)
    print(box, label, round(conf, 3), d.shape_matches(crop, label))

# 3. Regression check: test crops must still pass their own shape check
fs = glob.glob('Sign Cards/Test Images/cropped/*/*/*.png')
print(sum(d.shape_matches(cv2.imread(f), f.split('/')[3]) for f in fs), '/', len(fs))
```

Other techniques that found causes quickly:

- **Contact sheets.** Resize the crops to about 140 px, label each one, tile
  them with `np.hstack`/`np.vstack`, and look at the sheet. This is how the ear,
  nose, and arrow fragments were spotted.
- **Classifier-free search.** If the wrong label is always the same (e.g.
  stop), run `shape_matches(crop, 'stop')` on every proposal. Any non-sign
  that passes is a suspect, and you don't need the model to find it.
- **Draw proposals on the full frame.** Color the passing and failing boxes
  differently to see whether the whole sign was ever proposed.
- **Stress tests.** Apply motion blur (`cv2.filter2D` with a 1×k kernel),
  shift the crop off-center, and zoom in or out, then re-classify. This
  disproved the "rotation" hypothesis for pedestrianCrossing: tilted crops
  classified correctly at 99.9%.
- **Measure feature distributions** (hue, saturation, fill, corners,
  solidity) for false positives versus real signs, then choose a cutoff in the
  gap. If there's no gap, a filter can't fix it.

---

## 7. Results history

LCD outputs graded against the saved `detect_*` crops:

| Run | Changes in effect | Correct LCD outputs | Errors |
|---|---|---|---|
| 1 | Shape check, tight red range, solidity, 2-frame confirm, whole-sign proposals | 19 / 24 (79%) | 3 addedLane fragments → merge; "LIM" letters → keepRight; blurred pedestrianCrossing → merge |
| 2 | + diamond fill cap | 31 / 36 (86%) | 2 dark red close-up blobs → stop; 3 motion-blurred signs |
| 3 | + `--confirm-frames 3` | 32 / 32 (100%) | none |

Earlier runs (before detection saving) fixed the shirt/skin/ear → stop
problem, verified by re-running the pipeline on timed frames.

**Caveat:** run 3 was a single session in one room, under one person's
handling. It shows the filters work under those conditions, not that the
system is robust everywhere.

---

## 8. Known remaining issues

| Issue | Why the filters can't fix it | Real fix |
|---|---|---|
| Letter fragments from speed-limit signs → keepRight | Inner ink-shape count (§5.7) rejects most; two-glyph fragments ("LI") still pass | Retrain with partial crops / background class |
| Close-up dark red blobs (hand or shirt against the lens) → stop | Fill (0.70–0.87) and brightness (V ≈ 53) overlap with tight, dim test stops (fill up to 0.75, V down to 40) | Background class |
| Heavy motion blur | Whole-sign crops, so no shape test applies; confirmation hides it but doesn't fix it | Train with blur augmentation |
| Very dim stop signs may be missed | Solidity ≥ 0.9 rejects one dim test crop (0.80) | Better lighting, or retraining |
| Diamond at ~45° may be missed | Fill cap at 0.7 | Measure if it happens |
| Holder stick merging with the sign | Saturated stick joins the sign even in the color mask | Thinner/neutral stick, or retraining |
| Thresholds tuned on one room, one shirt, one person | Lighting shifts hue (warm light pushes red toward orange) | Re-measure in new conditions (§6) |

**Recommended next step:** retrain the combined model with an extra
background ("not a sign") class and BuggyBot camera crops: whole, partial,
blurred, and tilted signs, plus hands, faces, shirts, and room background.
The `detect_*` logging already collects exactly these hard cases. Training
requires explicit user approval (`AGENTS.md`).

---

## 9. Pitfalls that cost us time

- **`ssh -y` vs `ssh -Y`.** Lowercase `-y` sends logs to syslog; it does not
  forward X. (X forwarding is obsolete for this demo anyway.)
- **A mistyped `.local` name hangs** instead of failing, because mDNS waits
  for a timeout. Use `ssh -v` to see where it stalls.
- **Assuming a desktop exists.** The Pi is headless. Check `AGENTS.md` /
  `README.md` for device facts before suggesting GUI tools.
- **A stale LCD message** looks the same as a live one.
- **Guessing at causes.** Two guesses were wrong once measured: "rotation
  causes pedestrianCrossing → signalAhead" (tilted crops classified fine) and
  "it's the shirt" (it was mostly the face, ears, and nose). Measure first.
- **The test crops are cropped tighter than live crops.** The hand-cropped
  test photos have almost no margin, while `crop_square` adds 12%. So rules
  based on margin or edge contact ("the sign face shouldn't touch the crop
  edge") can't be checked against the test set: 289 of 329 test crops touch
  all four edges. Rules must hold on both, or the test set needs pipeline-style
  crops.
- **Copying only `*.jpg`** misses the detection PNGs.
- **Not clearing frame folders** mixes runs and corrupts the counts.

---

## 10. Rules for future changes

1. **Reproduce first.** Get the `detect_*` files for the failure and re-run
   the pipeline offline (§6) before editing anything.
2. **Measure, then choose a threshold in the gap.** Write down the
   distributions for false positives and true signs. If they overlap, a filter
   isn't the answer.
3. **Run the regression check after every filter change.** The test crops
   should stay at 328 / 329 (`stop/no_light/stop_001.png` is the known miss).
   Also re-check previously correct live `detect_*` crops.
4. **Comment the measurements in the code**, next to the threshold, as the
   existing filters do. A bare number gets "tuned" back into a bug.
5. **Prefer filters per class** (`SIGN_SHAPES`) over global changes to
   `make_candidates`. Proposal changes affect every sign.
6. **Remember what confirmation can and can't do:** it removes transient
   errors, never consistent ones.
7. **When filters run out, retrain** (with approval). Don't stack heuristics
   that tighten in ways that start rejecting real signs.
