# 03-2 · Enrollment

> **Level:** Intermediate · **Prerequisites:** [03-1 · Embeddings & matching](01_embeddings_and_matching.md)
> **Time:** 30 min · **Verified:** 2026-07-22 (opencv-contrib-python 4.11.0.86, bundled `samples/self/`)

## Why this matters

Enrollment is teaching the system your face: gather several normalized face crops, train an LBPH model, and save it. Do it well — varied but consistent images — and verification is reliable. Do it poorly — one image, weird lighting — and you'll get locked out (high FRR) or let others in (high FAR).

---

## Train and save a model

`enroll.py` reads a directory of images, normalizes each with `prepare_face()`, trains LBPH, and writes a model file:

```python
# faceunlock/enroll.py  (core)
import cv2, glob, os
import numpy as np
from .pipeline import prepare_face

ENROLLED_LABEL = 1

def train_model(image_paths, detect=True):
    faces = []
    for p in image_paths:
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        face = prepare_face(img, detect=detect)   # detect+crop, or use whole image
        if face is not None:
            faces.append(face)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array([ENROLLED_LABEL] * len(faces)))
    return recognizer, len(faces)
```

Run it on the bundled sample faces (pre-cropped, so `--no-detect`):

```bash
python -m faceunlock.enroll --images samples/self --model model.yml --no-detect
```

**Output (real run):**
```
Enrolled 8 images -> model.yml
```

`model.yml` is the saved template — the LBPH histograms for label 1. That's the file the verifier (and later PAM) loads.

---

## Enrolling *your* face (live)

On your machine, capture from the webcam instead (`capture.py` detects and crops each frame):

```bash
python -m faceunlock.capture --out samples/self --count 8   # grab 8 face crops
python -m faceunlock.enroll  --images samples/self --model model.yml --no-detect
```

`capture.py` already detect-crops, so the saved images are faces → enroll with `--no-detect`.

> **Tip — enroll well:** capture **8–15** images with small natural variation (slight head turns, normal vs smiling, your usual lighting). Too few or too uniform → brittle. Include your everyday conditions (glasses on/off if you switch) so verification isn't surprised.

> ⚠️ **`detect=True` will happily enroll a photo.** If someone holds a printed photo of you to the camera during enrollment, that gets enrolled too. Enroll in a trusted setting — and remember 2D can't tell the difference ([Section 04](../04_liveness_and_antispoofing/README.md)).

---

## Where the model lives (preview)

For learning, `model.yml` sits in your project. For the real `sudo` integration ([05-2](../05_pam_integration/02_wiring_sudo.md)), it moves to a **root-owned** location per user — `/etc/faceunlock/models/<username>.yml` — so a normal user can't swap in their own model and impersonate you. Treat the model as a credential.

---

## Recap & next

- ✅ Enrollment = normalize N face images → `LBPHFaceRecognizer.train` → save `model.yml`.
- ✅ Bundled samples enroll with `--no-detect`; webcam capture detect-crops first.
- ✅ Enroll 8–15 varied-but-consistent images in your real conditions for a reliable model.
- ✅ The model is a credential — store it root-owned for real use.
- ✅ Self-check: why might enrolling a single, brightly-lit image cause false rejects later?

→ Next: **[03-3 · The verify CLI](03_verify_cli.md)**

## Exercises

1. Enroll from `samples/self`, then re-enroll adding a copy of `samples/other.png` into the folder. Predict what that does to later impostor rejection.

<details>
<summary>Solution</summary>

Adding the other person's image to the enrolled label teaches the model that face *is* you → its distance drops → it may now be **falsely accepted**. Enrollment hygiene (only your face) is a security control, not just accuracy.
</details>
