# LISA camera-crop grayscale check

Analysis date: October 17, 2026. This used the saved LISA model; no training was run.

## Question

Did the difference between grayscale-looking LISA training images and color camera photos contribute to LISA's 47.7% camera-crop accuracy?

## Paired comparison

The same 329 sign-card crops were evaluated twice with `models/lisa_model.keras`:

1. Original RGB crops: PNG decode to RGB, resize to 32 × 32 with TensorFlow's default bilinear resize, 0–255 floating-point values. This matches `scripts/evaluate_sign_photos.py`.
2. The same resized crops converted with `tf.image.rgb_to_grayscale`, then repeated into three channels with `tf.image.grayscale_to_rgb`. No other input or model change.

| Input | Correct / 329 | Top-1 accuracy |
| --- | ---: | ---: |
| Original color | 157 | 47.7% |
| Grayscale conversion | 196 | 59.6% |

Grayscale conversion fixed 61 originally incorrect predictions and changed 22 originally correct predictions to incorrect ones: a net improvement of 39 images (11.9 percentage points).

## Interpretation

Inspection of LISA's prepared training crops shows many grayscale or near-grayscale images. Small residual RGB differences mean a strict channel-equality count does not reliably measure the number of grayscale-looking images. This check does not establish a precise grayscale percentage in the training set.

None of the 329 original camera crops met a near-exact grayscale criterion of maximum per-pixel RGB channel spread ≤2 on an 8-bit scale. Visually, even the black-and-white sign designs retain camera/background color. Black-and-white artwork is not the same as a grayscale image.

The paired test supports sensitivity to color/preprocessing as a contributing factor. It does **not** establish that grayscale training data caused all of LISA's errors: grayscale input still left 133/329 predictions incorrect. Establishing the effect of training-image color independently would require a controlled training comparison, which was not performed.

Sources: `sign_photo_test_report.json`, `../scripts/evaluate_sign_photos.py`, `../models/lisa_model.keras`, the prepared LISA training crops, and the committed camera crops. The private analysis scripts and raw result JSON are retained in `.codex-slide-work/build/` at repository root.
