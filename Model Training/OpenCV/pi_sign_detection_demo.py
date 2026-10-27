#!/usr/bin/env python3
"""BuggyBot CM5: Pi Camera -> OpenCV proposals -> LiteRT classification -> overlays/LCD.

Install as documented in Hardware/README.md and run this script from anywhere.
No motors are accessed. No GPIO pins are claimed; line sensors can stay wired.

OpenCV proposals are heuristic, not an object-detection model. They may miss signs
or classify background. A classification confidence is NOT a sign-detection score.
"""
import argparse
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]  # intended location: Hardware/scripts/
MODEL_DIR = ROOT / "Model Training" / "models"
MODEL_PATH = MODEL_DIR / "combined_model.tflite"
LABELS_PATH = MODEL_DIR / "combined_model_labels.txt"
LCD_LIB = Path('/home/buggybot/LCD1602-RGB-Module-demo/Raspberry')

# Demo states: SEARCHING runs detection every frame; DISPLAYING holds one
# result on the LCD and skips detection until the hold time expires.
SEARCHING = 'SEARCHING'
DISPLAYING = 'DISPLAYING'

# Expected sign face for each class: (color mask, shape). The classifier has no
# "not a sign" class, so it labels any red blob (a hand, a shirt) as the
# nearest sign. Checking the crop's color and outline rejects those.
SIGN_SHAPES = {
    'stop': ('red', 'octagon'),
    'school': ('yellow', 'pentagon'),
    'pedestrianCrossing': ('yellow', 'pentagon'),
    'addedLane': ('yellow', 'diamond'),
    'merge': ('yellow', 'diamond'),
    'signalAhead': ('yellow', 'diamond'),
    'keepRight': ('white', 'rectangle'),
    'speedLimit25': ('white', 'rectangle'),
    'speedLimit30': ('white', 'rectangle'),
    'speedLimit35': ('white', 'rectangle'),
    'speedLimit45': ('white', 'rectangle'),
    'speedLimit65': ('white', 'rectangle'),
}


def arguments():
    p = argparse.ArgumentParser(description='BuggyBot automatic Pi Camera sign recognition demo')
    p.add_argument('--model', type=Path, default=MODEL_PATH)
    p.add_argument('--labels', type=Path, default=LABELS_PATH)
    p.add_argument('--width', type=int, default=1280)
    p.add_argument('--height', type=int, default=720)
    p.add_argument('--threshold', type=float, default=.85, help='minimum classifier confidence to show')
    p.add_argument('--max-candidates', type=int, default=8)
    p.add_argument('--stream', type=int, default=8000, metavar='PORT',
                   help='serve annotated video at http://buggybot.local:PORT; 0 disables')
    p.add_argument('--lcd', action=argparse.BooleanOptionalAction, default=True,
                   help='write highest-confidence match to Waveshare RGB1602 (--no-lcd disables)')
    p.add_argument('--confirm-frames', type=int, default=2,
                   help='consecutive frames that must agree on a label before it is shown')
    p.add_argument('--display-seconds', type=float, default=3.0,
                   help='seconds to hold a detected sign on the LCD before searching again')
    p.add_argument('--save-every', type=float, default=2.0, help='seconds between saved annotated frames (0 disables)')
    p.add_argument('--output', type=Path, default=Path.home() / 'buggybot_sign_demo')
    p.add_argument('--seconds', type=float, default=0, help='stop after N seconds; 0 means Ctrl+C')
    return p.parse_args()


def load_interpreter(path):
    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError:
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError as exc:
            raise RuntimeError('Missing LiteRT: ~/buggybot-venv/bin/pip install ai-edge-litert') from exc
    if not path.is_file():
        raise FileNotFoundError(f'Model missing: {path}')
    interpreter = Interpreter(model_path=str(path))
    interpreter.allocate_tensors()
    return interpreter


def classify(interpreter, labels, bgr_crop):
    # Match Hardware/scripts/buggybot_integration.py exactly: BGR -> RGB, 32x32,
    # float32 0..255; model contains its own rescaling.
    rgb = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (32, 32), interpolation=cv2.INTER_LINEAR)
    input_info = interpreter.get_input_details()[0]
    tensor = rgb.astype(np.float32)[np.newaxis, ...]
    if tuple(input_info['shape']) != tuple(tensor.shape):
        raise RuntimeError(f'Unexpected model input shape {input_info["shape"]}; expected (1,32,32,3)')
    if input_info['dtype'] != np.float32:
        raise RuntimeError(f'Unexpected model dtype {input_info["dtype"]}; repo script expects float32')
    interpreter.set_tensor(input_info['index'], tensor)
    interpreter.invoke()
    result = interpreter.get_tensor(interpreter.get_output_details()[0]['index'])[0]
    best = int(np.argmax(result))
    if best >= len(labels):
        raise RuntimeError('Model outputs do not match label count')
    return labels[best], float(result[best])


def make_candidates(frame, max_count):
    """Find square-ish/high-contrast/colored sign-like objects.

    Includes contour proposals from both saturation masks and edges, so white
    speed-limit cards and red/yellow sign cards have a chance of being found.
    """
    h, w = frame.shape[:2]
    scaled = cv2.resize(frame, (640, max(1, round(h * 640 / w))))
    sh, sw = scaled.shape[:2]
    hsv = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)
    sat = cv2.inRange(hsv, (0, 75, 55), (179, 255, 255))
    sat = cv2.morphologyEx(sat, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edge = cv2.Canny(gray, 55, 155)
    edge = cv2.morphologyEx(edge, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    edge = cv2.dilate(edge, np.ones((3, 3), np.uint8), iterations=1)
    # Merge colored borders and grayscale edges. Both branches still contribute.
    combined = cv2.bitwise_or(sat, edge)
    box_records = []
    # Color alone too: edges of whatever holds the sign (a stick, a hand) can
    # merge with its outline in the other masks, leaving only inner pieces
    # (one arrow of addedLane, which reads as merge).
    for mask in (combined, edge, sat):
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area < (sw * sh) * .0006 or area > (sw * sh) * .55:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            if min(bw, bh) < 18:
                continue
            aspect = bw / max(1, bh)
            if not (.65 <= aspect <= 1.5):
                continue
            if x <= 1 or y <= 1 or x + bw >= sw - 1 or y + bh >= sh - 1:
                continue
            extent = area / max(1, bw * bh)
            if extent < .18:
                continue
            bx = int(x * w / sw)
            by = int(y * h / sh)
            bwidth = int(bw * w / sw)
            bheight = int(bh * h / sh)
            # Score favors sign-sized regions but avoids overspecifying sign shape.
            score = min(area / (sw * sh), .10) + .015 * (1 - abs(1 - aspect))
            box_records.append((score, (bx, by, bwidth, bheight)))
    # Deduplicate nested proposals, including different-sized contours of one sign.
    chosen = []
    for score, box in sorted(box_records, key=lambda t: t[0], reverse=True):
        x, y, bw, bh = box
        cx, cy = x + bw / 2, y + bh / 2
        duplicate = False
        for ax, ay, aw, ah in chosen:
            acx, acy = ax + aw / 2, ay + ah / 2
            # Center overlap and similar scale indicates duplicate proposals.
            close = abs(cx - acx) < .18 * max(bw, aw) and abs(cy - acy) < .18 * max(bh, ah)
            similar = .45 < (bw * bh) / max(1, aw * ah) < 2.2
            if close and similar:
                duplicate = True
                break
        if not duplicate:
            chosen.append(box)
        if len(chosen) >= max_count:
            break
    return chosen


def contains(outer, inner):
    """True when box inner lies inside box outer (x, y, w, h)."""
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return ox <= ix and oy <= iy and ix + iw <= ox + ow and iy + ih <= oy + oh


def crop_square(frame, box):
    x, y, bw, bh = box
    h, w = frame.shape[:2]
    # Margin to include the whole printed sign border.
    side = int(max(bw, bh) * 1.12)
    cx, cy = x + bw // 2, y + bh // 2
    x1, y1 = max(0, cx - side // 2), max(0, cy - side // 2)
    x2, y2 = min(w, cx + side // 2), min(h, cy + side // 2)
    return frame[y1:y2, x1:x2]


class FrameStream:
    """Holds the newest annotated frame as JPEG and serves it as an MJPEG stream.

    MJPEG is a sequence of JPEG images sent in one HTTP response
    (multipart/x-mixed-replace); browsers replace the image as each part arrives.
    The OS is headless, so this replaces an OpenCV window.
    """

    def __init__(self, port):
        self.jpeg = None
        self.ready = threading.Condition()
        stream = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                self.end_headers()
                try:
                    while True:
                        with stream.ready:
                            stream.ready.wait()  # block until the main loop publishes a frame
                            jpeg = stream.jpeg
                        self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
                except (BrokenPipeError, ConnectionResetError):
                    pass  # viewer closed the tab

            def log_message(self, *_):
                pass  # keep the terminal for detection output

        # Daemon threads so Ctrl+C on the main loop ends the program.
        self.server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def publish(self, frame):
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ok:
            with self.ready:
                self.jpeg = buf.tobytes()
                self.ready.notify_all()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def color_mask(hsv, color):
    if color == 'red':
        # Red hue wraps around 0/179. The printed stop card is magenta-side red
        # (hue ~176, sat ~150); skin and the pink shirt in our test frames were
        # orange-side (hue ~3) and duller (sat ~97), so both bounds are tight.
        return cv2.inRange(hsv, (0, 100, 25), (2, 255, 255)) | cv2.inRange(hsv, (165, 100, 25), (179, 255, 255))
    if color == 'yellow':  # includes fluorescent yellow-green school/ped signs
        return cv2.inRange(hsv, (15, 80, 40), (55, 255, 255))
    # White face: unsaturated and brighter than the crop's Otsu split, so it
    # adapts to dim and bright lighting.
    otsu, _ = cv2.threshold(hsv[..., 2], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.inRange(hsv, (0, 0, int(otsu)), (179, 70, 255))


def shape_matches(crop, label):
    """True when the crop's largest region of the class color has the class shape."""
    if label not in SIGN_SHAPES:
        return True
    color, expected = SIGN_SHAPES[label]
    mask = color_mask(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV), color)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False
    # Convex hull ignores the sign's lettering and symbols cut into the mask.
    region = max(contours, key=cv2.contourArea)
    hull = cv2.convexHull(region)
    area = cv2.contourArea(hull)
    _, _, bw, bh = cv2.boundingRect(hull)
    if area < .2 * crop.shape[0] * crop.shape[1]:
        return False  # sign face must fill a real part of the crop
    extent = area / max(1, bw * bh)  # 1.0 = fills its box, .5 = diamond
    perimeter = cv2.arcLength(hull, True)
    if expected == 'octagon':
        # Fine 1% tolerance: an octagon keeps 8 corners, a circle/ellipse
        # (round hand or shirt blob) breaks into 14+.
        corners = len(cv2.approxPolyDP(hull, .01 * perimeter, True))
        # Solidity = region area / hull area. A printed octagon is one solid
        # red shape (~.99); skin (ears, noses, hands) is shaded and lumpy, so
        # its red patches are concave (<= .80 in our live frames).
        solidity = cv2.contourArea(region) / max(1, area)
        return 7 <= corners <= 9 and extent >= .7 and solidity >= .9
    corners = len(cv2.approxPolyDP(hull, .03 * perimeter, True))
    if expected in ('diamond', 'pentagon'):
        # Shared range: a diamond clipped at the crop edge gains a corner.
        return 4 <= corners <= 6 and .4 <= extent <= .9
    return corners == 4 and extent >= .8  # rectangle


# LCD backlight (R, G, B) per sign color in SIGN_SHAPES; green while searching.
LCD_COLORS = {'red': (255, 0, 0), 'yellow': (255, 150, 0), 'white': (255, 255, 255)}
SEARCHING_COLOR = (0, 255, 0)


def setup_lcd(enabled):
    if not enabled:
        return None
    sys.path.insert(0, str(LCD_LIB))
    import RGB1602
    lcd = RGB1602.RGB1602(16, 2)
    lcd.setRGB(*SEARCHING_COLOR)
    lcd.clear()
    return lcd


def lcd_text(lcd, first, second):
    lcd.setCursor(0, 0)
    lcd.printout(first[:16].ljust(16))
    lcd.setCursor(0, 1)
    lcd.printout(second[:16].ljust(16))


def main():
    args = arguments()
    if not 0 <= args.threshold <= 1:
        raise ValueError('threshold must be between 0 and 1')
    args.output.mkdir(parents=True, exist_ok=True)
    if not args.labels.is_file():
        raise FileNotFoundError(f'Labels missing: {args.labels}')
    # The current BuggyBot integration script uses whitespace-separated labels.
    labels = args.labels.read_text().split()
    interpreter = load_interpreter(args.model)
    lcd = setup_lcd(args.lcd)
    stream = FrameStream(args.stream) if args.stream else None
    from picamera2 import Picamera2
    camera = Picamera2()
    try:
        camera.configure(camera.create_video_configuration(
            main={'size': (args.width, args.height), 'format': 'RGB888'}))
        camera.start()
        time.sleep(2)  # exposure settle
        print(f'Camera running {args.width}x{args.height} | model={args.model}')
        print(f'Saving frames to {args.output} | Ctrl+C to stop')
        if stream is not None:
            print(f'Streaming at http://buggybot.local:{args.stream}')
        start = time.monotonic()
        next_save = 0.0
        last_report = 0.0
        frames = 0
        state = SEARCHING
        display_until = 0.0
        # Confirmation: a label must be the best match on --confirm-frames
        # consecutive frames. One-frame errors (a blurred crop as a card moves
        # into view) reset the count instead of reaching the LCD.
        pending_label = None
        pending_count = 0
        if lcd is not None:
            lcd_text(lcd, 'SEARCHING...', 'NO SIGN FOUND')
        while True:
            now = time.monotonic()
            if args.seconds and now - start >= args.seconds:
                break
            frame = camera.capture_array('main')  # BGR for RGB888 on Picamera2
            frames += 1
            if state == SEARCHING:
                candidates = make_candidates(frame, args.max_candidates)
                matches = []
                for box in candidates:
                    crop = crop_square(frame, box)
                    if crop.size == 0:
                        continue
                    label, confidence = classify(interpreter, labels, crop)
                    if confidence >= args.threshold and shape_matches(crop, label):
                        matches.append((box, label, confidence))
                # Drop matches inside another match: a piece of a sign (one
                # arrow of addedLane) can classify as a different sign (merge).
                matches = [m for m in matches
                           if not any(o is not m and contains(o[0], m[0]) for o in matches)]
                for (x, y, bw, bh), label, confidence in matches:
                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
                    cv2.putText(frame, f'{label} {confidence:.1%}',
                                (x, max(25, y - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                                .65, (0, 255, 0), 2, cv2.LINE_AA)
                if now - last_report > 1.0:
                    print(f'Frame {frames}: {len(candidates)} regions | searching', flush=True)
                    last_report = now
                if matches:
                    _, label, confidence = max(matches, key=lambda m: m[2])
                    pending_count = pending_count + 1 if label == pending_label else 1
                    pending_label = label
                else:
                    pending_label, pending_count = None, 0
                if pending_count >= args.confirm_frames:
                    # Transition: SEARCHING -> DISPLAYING. LCD is written once here.
                    print(f'DETECTED {label} {confidence:.0%} | holding {args.display_seconds:g}s', flush=True)
                    if lcd is not None:
                        lcd.setRGB(*LCD_COLORS[SIGN_SHAPES[label][0]])
                        lcd_text(lcd, label, f'Confidence {confidence:.0%}')
                    state = DISPLAYING
                    display_until = now + args.display_seconds
                    pending_label, pending_count = None, 0
            elif state == DISPLAYING and now >= display_until:
                # Transition: DISPLAYING -> SEARCHING.
                print('Hold finished | searching', flush=True)
                if lcd is not None:
                    lcd.setRGB(*SEARCHING_COLOR)
                    lcd_text(lcd, 'SEARCHING...', 'NO SIGN FOUND')
                state = SEARCHING
            cv2.putText(frame, f'BuggyBot | {state}',
                        (15, 30), cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 2)
            if args.save_every > 0 and now >= next_save:
                filename = args.output / f'frame_{frames:06d}.jpg'
                cv2.imwrite(str(filename), frame)
                next_save = now + args.save_every
            if stream is not None:
                stream.publish(frame)
    except KeyboardInterrupt:
        print('\nDemo stopped')
    finally:
        camera.stop()
        camera.close()
        if lcd is not None:
            lcd_text(lcd, 'BUGGYBOT', 'DEMO COMPLETE')
        if stream is not None:
            stream.close()
        print('Camera released; demo finished.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
