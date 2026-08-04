# 03-1 · Embeddings & matching

> **Level:** Intermediate · **Prerequisites:** [02-2 · Face detection](../02_capturing_and_detecting/02_face_detection.md)
> **Time:** 25 min · **Verified:** 2026-07-22 (opencv-contrib-python 4.11.0.86)

## Why this matters

Recognition rests on one idea: turn a face into a vector of numbers (a **template**) such that *the same person's faces are close together and different people's are far apart*. Then "is this you?" becomes "is the distance small enough?". We use OpenCV's **LBPH** because you can understand it end to end; the same shape scales up to dlib's deep embeddings.

---

## LBPH in one paragraph

**Local Binary Patterns Histograms**: for each pixel, compare it to its 8 neighbors to get an 8-bit pattern (which neighbors are brighter). Do this across the face, bin the patterns into **histograms** over small regions, and concatenate them — that histogram vector *is* the template. Two faces are compared by the distance between their histograms. It's texture-based, fast, CPU-only, and trains on a handful of images.

```python
import cv2
# LBPH lives in the contrib module cv2.face:
recognizer = cv2.face.LBPHFaceRecognizer_create()
```

> **Preprocessing matters.** We normalize every face the same way before templating — grayscale → resize to a fixed 100×100 → **`cv2.equalizeHist`** (flatten the brightness histogram). Equalization is what makes the enrolled-vs-impostor gap clean: without it, a lighting change looks like a different person. This lives in `prepare_face()` ([capstone `pipeline.py`]).

---

## Matching = distance vs threshold

LBPH's `predict()` returns `(label, confidence)` where **confidence is a distance — LOWER is a better match**:

```python
label, confidence = recognizer.predict(face_crop)
accept = (label == ENROLLED_LABEL) and (confidence < THRESHOLD)
```

In our verified build the enrolled person scores **~48** and a different person **~88**, so a threshold of **70** separates them (full run in [03-3](03_verify_cli.md)). That single comparison is the entire "recognition" decision.

> ⚠️ **The name "confidence" is backwards from intuition.** In LBPH a *low* number means *high* confidence (small distance = good match). Read it as "distance". This trips up everyone once.

---

## The accuracy upgrade: dlib / `face_recognition`

LBPH is great for learning, mediocre for production (sensitive to pose/lighting, texture-only). The standard upgrade is **deep face embeddings** — dlib's CNN maps a face to a 128-D vector, and you compare with Euclidean distance (typical accept threshold ~0.6):

```python
# pip install face-recognition   (compiles dlib — heavier; optional)
# import face_recognition
# enc = face_recognition.face_encodings(image)[0]           # 128-D embedding
# match = face_recognition.compare_faces([enrolled_enc], enc, tolerance=0.6)
```

Same mental model — template, distance, threshold — just far more discriminative. **Howdy** (Section 06) uses exactly this. We teach LBPH because it's readable and dependency-light; we point at dlib because it's what you'd actually deploy.

| | LBPH (this course) | dlib embeddings (Howdy) |
|---|---|---|
| Template | LBP histogram | 128-D CNN embedding |
| Install | ships with opencv-contrib | compiles dlib (heavy) |
| Accuracy | modest | strong |
| Great for | learning the mechanics | production |

---

## Recap & next

- ✅ Recognition = face → **template**; matching = **distance < threshold**.
- ✅ LBPH templates are local-binary-pattern histograms; `predict()` returns a **distance** (lower = better).
- ✅ Normalize (grayscale, resize, `equalizeHist`) so lighting doesn't masquerade as identity.
- ✅ dlib/`face_recognition` (128-D embeddings) is the accuracy upgrade — same mental model.
- ✅ Self-check: LBPH `predict` returns 45 for face A and 95 for face B — which is the better match?

→ Next: **[03-2 · Enrollment](02_enrollment.md)**

## Exercises

1. Explain why `equalizeHist` improves the enrolled-vs-impostor separation, in terms of FAR/FRR.

<details>
<summary>Solution</summary>

Equalization removes brightness/contrast differences, so the *distance* mostly reflects facial texture rather than lighting. That shrinks the enrolled person's distance under varied lighting (lower FRR) without pulling impostors closer, widening the usable threshold gap.
</details>
