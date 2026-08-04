"""Offline tests — no webcam, no PAM, no network. Run: pytest -q

These verify the reproducible software core: detection finds a face, and the
enroll+verify pipeline accepts the enrolled identity while rejecting another.
"""
import glob
import pathlib

import cv2
import pytest

from faceunlock.pipeline import detect_faces, prepare_face, DEFAULT_THRESHOLD
from faceunlock.enroll import train_model
from faceunlock.verify import verify_face

SAMPLES = pathlib.Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture(scope="module")
def model():
    paths = sorted(glob.glob(str(SAMPLES / "self" / "*.png")))
    recognizer, n = train_model(paths, detect=False)
    assert n == 8
    return recognizer


def _face(name):
    img = cv2.imread(str(SAMPLES / name), cv2.IMREAD_GRAYSCALE)
    return prepare_face(img, detect=False)


def test_detection_finds_a_face():
    gray = cv2.imread(str(SAMPLES / "detect.png"), cv2.IMREAD_GRAYSCALE)
    faces = detect_faces(gray)
    assert len(faces) >= 1


def test_accepts_enrolled_identity(model):
    accepted, conf = verify_face(model, _face("self_test.png"), DEFAULT_THRESHOLD)
    assert accepted is True
    assert conf < DEFAULT_THRESHOLD


def test_rejects_other_identity(model):
    accepted, conf = verify_face(model, _face("other.png"), DEFAULT_THRESHOLD)
    assert accepted is False
    assert conf >= DEFAULT_THRESHOLD


def test_self_scores_better_than_other(model):
    _, self_conf = verify_face(model, _face("self_test.png"), DEFAULT_THRESHOLD)
    _, other_conf = verify_face(model, _face("other.png"), DEFAULT_THRESHOLD)
    assert self_conf < other_conf          # the enrolled face is the closer match
