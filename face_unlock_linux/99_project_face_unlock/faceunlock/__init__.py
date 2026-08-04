"""faceunlock — a minimal, offline-verifiable face authenticator.

Pipeline: detect (Haar cascade) -> preprocess (grayscale, resize, equalize) ->
recognize (LBPH) -> threshold -> accept/reject. The `verify` CLI returns exit 0
(accept) or exit 1 (reject), which is exactly what a PAM `pam_exec` hook needs.

Educational, NOT production security. See the course's security-reality lesson.
"""
from .pipeline import prepare_face, detect_faces, FACE_SIZE, DEFAULT_THRESHOLD

__all__ = ["prepare_face", "detect_faces", "FACE_SIZE", "DEFAULT_THRESHOLD"]
