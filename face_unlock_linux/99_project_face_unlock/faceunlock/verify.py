"""Verify a face against an enrolled model. Exit 0 = accept, exit 1 = reject.

That exit code is the whole point: PAM's `pam_exec` treats exit 0 as auth success.

Usage (offline, from an image):
    python -m faceunlock.verify --model model.yml --image samples/self_test.png --no-detect
Usage (live, from the webcam):
    python -m faceunlock.verify --model model.yml            # add --threshold N to tune
"""
import argparse
import sys

import cv2

from .pipeline import prepare_face, DEFAULT_THRESHOLD
from .enroll import ENROLLED_LABEL


def verify_face(recognizer, face, threshold: float):
    """Return (accepted: bool, confidence: float). Lower confidence = better match."""
    label, confidence = recognizer.predict(face)
    accepted = (label == ENROLLED_LABEL) and (confidence < threshold)
    return accepted, confidence


def _load_image_face(path, detect):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Could not read image: {path}", file=sys.stderr)
        return None
    return prepare_face(img, detect=detect)


def _capture_face(detect=True, camera=0):
    cap = cv2.VideoCapture(camera)
    try:
        ok, frame = cap.read()
        if not ok:
            return None
        return prepare_face(frame, detect=detect)
    finally:
        cap.release()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="model.yml")
    ap.add_argument("--image", help="verify this image instead of the webcam")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--no-detect", action="store_true", help="input is an already-cropped face")
    args = ap.parse_args()

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(args.model)

    detect = not args.no_detect
    face = _load_image_face(args.image, detect) if args.image else _capture_face(detect)
    if face is None:
        print("REJECT: no face found", file=sys.stderr)
        sys.exit(1)                                    # fail closed

    accepted, confidence = verify_face(recognizer, face, args.threshold)
    if accepted:
        print(f"ACCEPT (confidence {confidence:.1f} < {args.threshold})")
        sys.exit(0)
    print(f"REJECT (confidence {confidence:.1f} >= {args.threshold})", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
