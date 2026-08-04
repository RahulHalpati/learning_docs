# 02-1 · Webcam capture

> **Level:** Beginner · **Prerequisites:** [01-3 · Environment & safety](../01_foundations/03_environment_and_safety.md)
> **Time:** 20 min · **Verified:** 2026-07-22 (opencv-contrib-python 4.11.0.86; live capture is hardware-attested)

## Why this matters

Everything downstream operates on an image. OpenCV gives you one API for both sources you'll use: a **file** (offline, reproducible — for learning and tests) and the **webcam** (live — the real thing). Get comfortable with both; the rest of the pipeline doesn't care where the pixels came from.

---

## Reading an image (offline)

```python
import cv2

img = cv2.imread("samples/detect.png", cv2.IMREAD_GRAYSCALE)   # HxW numpy array
print("shape:", img.shape, "dtype:", img.dtype)
```

**Output (real run):**
```
shape: (320, 320) dtype: uint8
```

An image is just a NumPy array of pixel values. Grayscale (one channel) is all face detection/LBPH need, and it's what we use throughout — color adds nothing for recognition and triples the data.

---

## Capturing from the webcam (live, on your machine)

```python
import cv2

cap = cv2.VideoCapture(0)          # /dev/video0
if not cap.isOpened():
    raise SystemExit("Could not open camera — check `ls /dev/video*` and permissions.")

ok, frame = cap.read()             # grab one frame (BGR color, HxWx3)
cap.release()                      # ALWAYS release the device
if ok:
    cv2.imwrite("frame.png", frame)
    print("captured", frame.shape)
```

Key points:

- `VideoCapture(0)` opens the first camera; the index matches `/dev/videoN`.
- `read()` returns `(ok, frame)` — **always check `ok`**; cameras fail, are busy, or need a warm-up frame.
- **`release()`** frees the device so other apps (and your next run) can use it. Wrap in `try/finally`.
- Frames are **BGR**, not RGB (an OpenCV quirk) — irrelevant once we convert to grayscale.

> **Tip:** the first frame after opening is sometimes black/garbage while the sensor warms up. For enrollment, grab several frames (as `capture.py` does in the capstone) and discard early ones.

> ⚠️ **Privacy:** the camera is a sensor on *you*. Only capture on a machine you control, tell anyone sharing it, and store enrollment images/templates like secrets (Section 05 puts them in root-owned `/etc/faceunlock`).

---

## Why we default to files in this course

Live capture can't be reproduced in a tutorial (no two runs are identical, and CI has no face). So Sections 02–03 verify against **bundled sample images**, and the same functions accept a live frame unchanged. The capstone's `capture.py` is the webcam front door; everything else works on arrays.

---

## Recap & next

- ✅ An image is a NumPy array; grayscale is all we need.
- ✅ `VideoCapture(idx)` → `read()` (check `ok`) → `release()` (always).
- ✅ Frames are BGR; the course works from files for reproducibility, live frames drop in unchanged.
- ✅ Self-check: why must you call `release()`, and why check the `ok` flag from `read()`?

→ Next: **[02-2 · Face detection](02_face_detection.md)**

## Exercises

1. Write a loop that grabs 5 frames, discards the first 2 (warm-up), and saves the rest. (Needs a webcam.)

<details>
<summary>Solution</summary>

```python
cap = cv2.VideoCapture(0)
try:
    for i in range(5):
        ok, frame = cap.read()
        if ok and i >= 2:
            cv2.imwrite(f"f{i}.png", frame)
finally:
    cap.release()
```
Discarding warm-up frames avoids enrolling a black image.
</details>
