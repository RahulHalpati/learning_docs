"""Detection demo: report face boxes in an image. Offline, no webcam.

Usage:
    python -m faceunlock.detect --image samples/detect.png
"""
import argparse

import cv2

from .pipeline import detect_faces


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    args = ap.parse_args()

    gray = cv2.imread(args.image, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise SystemExit(f"Could not read image: {args.image}")

    faces = detect_faces(gray)
    print(f"Found {len(faces)} face(s):")
    for (x, y, w, h) in faces:
        print(f"  box x={x} y={y} w={w} h={h}")


if __name__ == "__main__":
    main()
