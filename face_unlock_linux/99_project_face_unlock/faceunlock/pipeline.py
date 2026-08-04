"""Shared image pipeline: detection + preprocessing.

Kept tiny and dependency-light (just OpenCV + numpy) so every step is easy to
follow and runs offline on static images — no webcam required.
"""
import cv2
import numpy as np

FACE_SIZE = (100, 100)          # LBPH needs consistent-size grayscale crops
DEFAULT_THRESHOLD = 70.0        # LBPH distance: LOWER = better match; below this = accept

_CASCADE = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


def load_detector() -> cv2.CascadeClassifier:
    det = cv2.CascadeClassifier(_CASCADE)
    if det.empty():
        raise RuntimeError(f"Could not load Haar cascade at {_CASCADE}")
    return det


def detect_faces(gray: np.ndarray):
    """Return a list of (x, y, w, h) face boxes in a grayscale image."""
    return load_detector().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40)
    )


def _to_gray(image) -> np.ndarray:
    if image.ndim == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def prepare_face(image, detect: bool = True):
    """Turn an image into a normalized face crop ready for LBPH.

    detect=True  : find the largest face and crop it (use for webcam frames).
    detect=False : treat the whole image as an already-cropped face (use for the
                   pre-cropped sample images).
    Returns a FACE_SIZE grayscale, histogram-equalized array, or None if
    detect=True and no face is found.
    """
    gray = _to_gray(image)
    if detect:
        faces = detect_faces(gray)
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda b: b[2] * b[3])   # largest face
        gray = gray[y:y + h, x:x + w]
    gray = cv2.resize(gray, FACE_SIZE)
    return cv2.equalizeHist(gray)                            # normalize lighting
