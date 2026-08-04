"""Enroll a face: train an LBPH model from a directory of images and save it.

Usage:
    python -m faceunlock.enroll --images samples/self --model model.yml [--no-detect]

Each image becomes a training sample for label 1 (the enrolled user). The model
is saved as OpenCV YAML. `--no-detect` treats images as already-cropped faces
(the sample set is pre-cropped; webcam captures are not).
"""
import argparse
import glob
import os

import cv2
import numpy as np

from .pipeline import prepare_face

ENROLLED_LABEL = 1


def train_model(image_paths, detect=True):
    faces = []
    for p in image_paths:
        img = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        face = prepare_face(img, detect=detect)
        if face is not None:
            faces.append(face)
    if not faces:
        raise SystemExit("No usable faces found to enroll.")
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array([ENROLLED_LABEL] * len(faces)))
    return recognizer, len(faces)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, help="directory of enrollment images")
    ap.add_argument("--model", default="model.yml", help="output model path")
    ap.add_argument("--no-detect", action="store_true", help="images are already cropped faces")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.images, "*")))
    recognizer, n = train_model(paths, detect=not args.no_detect)
    recognizer.write(args.model)
    print(f"Enrolled {n} images -> {args.model}")


if __name__ == "__main__":
    main()
