# Sample images — provenance & license

The face images here are derived from the **Olivetti / AT&T "Database of Faces"**
(40 subjects, 64×64 grayscale), retrieved via `scikit-learn`'s
`sklearn.datasets.fetch_olivetti_faces()`.

The AT&T Laboratories Cambridge terms permit use of the images **for any purpose**,
provided their origin is acknowledged. They are used here purely as neutral,
license-clean test data so the pipeline and tests run offline without a webcam.

- `self/01.png … 08.png` — 8 images of one subject (the "enrolled user").
- `self_test.png` — a held-out image of the same subject → should **accept**.
- `other.png` — a different subject → should **reject**.
- `detect.png` — a face upscaled and padded so the Haar detector has margin.

These are **not** photos of any course author or user. Regenerate with
`python gen_samples.py samples` (see the course's build notes) if needed.
