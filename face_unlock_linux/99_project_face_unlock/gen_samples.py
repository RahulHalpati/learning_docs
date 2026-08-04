"""Generate license-clean sample face images for the capstone (offline verification).

Uses the Olivetti (AT&T) faces dataset via scikit-learn — 40 subjects x 10 images,
64x64 grayscale. The AT&T faces license permits use for any purpose. We save a few
derived PNGs so the course itself needs only opencv-contrib-python (no sklearn).

Layout produced under DEST:
  self/01.png ... self/08.png   # enrolled identity (subject A, 8 images)
  self_test.png                 # held-out image of subject A (should ACCEPT)
  other.png                     # a different subject (should REJECT)
  detect.png                    # a padded/upscaled face for Haar detection demo
"""
import sys, pathlib
import numpy as np
from PIL import Image
from sklearn.datasets import fetch_olivetti_faces

DEST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "samples")
(DEST / "self").mkdir(parents=True, exist_ok=True)

data = fetch_olivetti_faces()
images = (data.images * 255).astype("uint8")   # (400, 64, 64) float->uint8
targets = data.target

SELF, OTHER = 1, 10
self_idx = np.where(targets == SELF)[0]
other_idx = np.where(targets == OTHER)[0]

for n, i in enumerate(self_idx[:8], start=1):
    Image.fromarray(images[i]).save(DEST / "self" / f"{n:02d}.png")
Image.fromarray(images[self_idx[9]]).save(DEST / "self_test.png")   # held-out self
Image.fromarray(images[other_idx[0]]).save(DEST / "other.png")      # different person

# Detection demo: upscale 3x and pad with a gray border so Haar has margin.
face = images[self_idx[0]]
big = np.array(Image.fromarray(face).resize((192, 192), Image.BICUBIC))
canvas = np.full((320, 320), 128, dtype="uint8")
canvas[64:256, 64:256] = big
Image.fromarray(canvas).save(DEST / "detect.png")

print("wrote samples to", DEST.resolve())
for p in sorted(DEST.rglob("*.png")):
    print("  ", p.relative_to(DEST))
