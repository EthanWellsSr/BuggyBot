# OpenCV Sign Demo

`pi_sign_detection_demo.py` is BuggyBot's live sign-recognition demo. It runs
on the CM5 and does not drive the motors.

1. The Pi Camera captures a frame.
2. OpenCV finds regions in the frame that look like signs.
3. The combined TFLite model classifies each region.
4. Color and shape checks reject regions that can't be the predicted sign.
5. When the same sign is read on 3 frames in a row, the LCD shows it.

In the final live test, all 10 printed sign classes were shown 3 times each
across two runs, and 60 of 60 LCD outputs were correct. Those runs were done in
one room, under one lighting setup.

## Files

| File | Purpose |
|---|---|
| `pi_sign_detection_demo.py` | The demo |
| [`OpenCV_troubleshooting_guide.md`](OpenCV_troubleshooting_guide.md) | How the pipeline works, every problem found during testing, the measurements behind each fix, and how to debug new errors. **Read it before changing the detection logic or thresholds.** |

## Requirements

Run `Hardware/setup.sh` on BuggyBot. It installs Picamera2 and OpenCV, and
creates `~/buggybot-venv` with LiteRT. The demo loads the model from
`Model Training/models/combined_model.tflite` and the labels from
`combined_model_labels.txt`. It loads the LCD library from
`/home/buggybot/LCD1602-RGB-Module-demo/Raspberry`.

## Run

From the repository root on BuggyBot:

```bash
~/buggybot-venv/bin/python "Model Training/OpenCV/pi_sign_detection_demo.py"
```

To watch the camera, open `http://buggybot.local:8000` in a browser on the same
network. BuggyBot runs Raspberry Pi OS Lite with no desktop, so there is no
preview window on the Pi. Press Ctrl+C to stop.

While a sign is held on the LCD, the stream shows it as a large bar across the
bottom of the video in the LCD's color, so the result reads when the browser is
projected.

### LCD

| State | Backlight |
|---|---|
| Searching | Green, `SEARCHING...` |
| Stop sign | Red |
| Yellow signs (school, pedestrianCrossing, merge, addedLane, signalAhead) | Amber |
| White signs (speed limits, keepRight) | White |

Each detection is held on the LCD for 3 seconds, then the demo goes back to
searching.

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--stream PORT` | 8000 | Video stream port; `0` turns it off |
| `--lcd / --no-lcd` | on | Write detections to the LCD |
| `--confirm-frames` | 3 | Consecutive frames that must agree before output |
| `--threshold` | 0.85 | Minimum classifier confidence |
| `--display-seconds` | 3.0 | How long a detection stays on the LCD |
| `--save-every` | 2.0 | Seconds between saved frames; `0` turns it off |
| `--output` | `~/buggybot_sign_demo` | Folder for saved frames |
| `--width` / `--height` | 1280 / 720 | Camera resolution |
| `--seconds` | 0 | Stop after N seconds; `0` runs until Ctrl+C |

## Saved output

Saved files go to `~/buggybot_sign_demo` on the Pi:

- `frame_NNNNNN.jpg`: an annotated frame every 2 seconds.
- `detect_NNNNNN_<label>_frame.png` and `..._crop.png`: the full frame and the
  exact crop behind every LCD output. Use these to reproduce a bad detection
  (see section 6 of the troubleshooting guide).

Copy everything to a laptop, then clear the Pi folder before the next run:

```bash
scp "buggybot@buggybot.local:~/buggybot_sign_demo/*" ~/Desktop/BuggyBot/scratch_frames/
```

```bash
rm -r ~/buggybot_sign_demo
```

`scratch_frames/` is Git-ignored.

## Known limits

- The model has no "not a sign" class. The color and shape checks filter its
  mistakes, but they don't fix the cause.
- Thresholds were tuned in one room under one lighting setup.
- Speed limits 30 and 35 have not been tested live.
- Distance and viewing angle have not been measured. CM5 inference averaged
  1.9 ms per crop (36 fps) in the 10/28 integration test.

See section 8 of the troubleshooting guide for details.
