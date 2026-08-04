"""Capture enrollment images from the webcam. Requires a camera (runs on YOUR machine).

Usage:
    python -m faceunlock.capture --out samples/self --count 8

Grabs `count` frames from the webcam, detects the face in each, and saves the
cropped, normalized face. Detection means a photo held to the camera is captured
just like a real face — that's the spoofing weakness Section 04 addresses.
"""
import argparse
import os
import time

import cv2

from .pipeline import prepare_face


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise SystemExit("Could not open camera. Check `ls /dev/video*` and permissions.")

    saved = 0
    try:
        while saved < args.count:
            ok, frame = cap.read()
            if not ok:
                continue
            face = prepare_face(frame, detect=True)
            if face is not None:
                path = os.path.join(args.out, f"{saved + 1:02d}.png")
                cv2.imwrite(path, face)
                saved += 1
                print(f"saved {path}")
                time.sleep(0.3)          # small gap so samples vary slightly
    finally:
        cap.release()
    print(f"Captured {saved} face image(s) to {args.out}")


if __name__ == "__main__":
    main()
