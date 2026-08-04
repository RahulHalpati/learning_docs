# 02-2 · Face detection

> **Level:** Beginner · **Prerequisites:** [02-1 · Webcam capture](01_webcam_capture.md)
> **Time:** 25 min · **Verified:** 2026-07-22 (opencv-contrib-python 4.11.0.86, bundled `samples/detect.png`)

## Why this matters

Before you can *recognize* a face, you must *find* it — a photo is mostly background. **Detection** answers "is there a face, and where?"; **recognition** (next section) answers "whose face?". OpenCV ships a classic detector — the **Haar cascade** — that runs in milliseconds on a CPU and needs no training.

> **Analogy — highlighter then reader.** Detection highlights the face in the page; recognition reads who it is. You highlight first so the reader isn't distracted by the whole page.

---

## Haar cascades

A Haar cascade is a pre-trained classifier that slides windows over the image looking for face-like light/dark patterns (eyes darker than cheeks, etc.), in a fast cascade of stages that reject non-faces early. OpenCV bundles trained cascades — no setup:

```python
import cv2

# The frontal-face cascade ships with opencv-contrib-python (4.x).
cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
detector = cv2.CascadeClassifier(cascade_path)
assert not detector.empty(), "cascade failed to load"
```

> ⚠️ If `detector.empty()` is true, you're likely on **OpenCV 5.x** (cascades removed) or the non-contrib build. Use `opencv-contrib-python==4.11.0.86` ([01-3](../01_foundations/03_environment_and_safety.md)).

---

## Detecting faces

```python
import cv2

detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
gray = cv2.imread("samples/detect.png", cv2.IMREAD_GRAYSCALE)

faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
print(f"Found {len(faces)} face(s):")
for (x, y, w, h) in faces:
    print(f"  box x={x} y={y} w={w} h={h}")
```

**Output (real run):**
```
Found 1 face(s):
  box x=37 y=14 w=253 h=253
```

Each result is a bounding box `(x, y, w, h)`. Here one face was found; to **crop** it you slice the array: `gray[y:y+h, x:x+w]` — that crop is what recognition consumes.

### The knobs

| Parameter | Effect | Trade-off |
|-----------|--------|-----------|
| `scaleFactor` (1.05–1.4) | image pyramid step | smaller = more scales, slower, more sensitive |
| `minNeighbors` (3–6) | how many overlapping hits confirm a face | higher = fewer false positives, may miss faces |
| `minSize` | ignore boxes smaller than this | skips tiny background patterns |

These trade **misses vs false detections** — the detection-stage echo of the FAR/FRR trade-off from [01-1](../01_foundations/01_how_face_auth_works.md).

---

## Picking one face

For unlock you want *the* face — the subject in front of the camera — so take the **largest** box (closest/most prominent):

```python
if len(faces):
    x, y, w, h = max(faces, key=lambda b: b[2] * b[3])   # largest area
    face_crop = gray[y:y+h, x:x+w]
```

This is exactly what the capstone's `prepare_face()` does before handing the crop to LBPH.

> **Tip:** Haar wants a **frontal, reasonably lit** face with margin around it. It struggles with profiles, heavy shadow, or a face filling the whole frame with no margin. Better detectors exist (DNN face detectors, dlib HOG/CNN); Haar is the fast, zero-dependency default that's perfect for learning.

---

## Recap & next

- ✅ Detection finds *where* a face is; recognition (next) finds *who*.
- ✅ `CascadeClassifier` + `detectMultiScale` returns `(x,y,w,h)` boxes; crop with array slicing.
- ✅ `scaleFactor`/`minNeighbors`/`minSize` trade misses against false detections.
- ✅ For unlock, take the **largest** box.
- ✅ Self-check: raising `minNeighbors` makes detection do what — miss more, or false-detect more?

→ Next: **[03 · Recognition & enrollment](../03_recognition_and_enrollment/README.md)**

## Exercises

1. Run detection on `samples/detect.png` with `minNeighbors=10`, then `=2`. How does the face count change, and why?

<details>
<summary>Solution</summary>

Higher `minNeighbors` (10) demands more corroborating detections → stricter, may drop to 0 on a marginal image. Lower (2) is lax → may report extra spurious boxes. It's the detector's precision/recall dial.
</details>
