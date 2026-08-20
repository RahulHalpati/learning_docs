"""Test fixtures. The sample video is *generated* by ffmpeg, not committed.

No binary blobs in the repo, and the media is byte-identical on every machine —
`testsrc` and `sine` are deterministic synthetic sources.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@pytest.fixture(scope="session")
def sample(tmp_path_factory) -> Path:
    """12s 640x360 test video: sound 0-4s, silence 4-8s, sound 8-12s.

    That structure gives silence detection something real to find, so the
    analysis tests assert on genuine output rather than an empty list.
    """
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")

    out = tmp_path_factory.mktemp("media") / "sample.mp4"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "testsrc=size=640x360:rate=25:duration=12",
         "-f", "lavfi", "-i",
         "sine=frequency=440:duration=4,adelay=0|0",
         "-f", "lavfi", "-i", "anullsrc=duration=4",
         "-f", "lavfi", "-i", "sine=frequency=660:duration=4",
         "-filter_complex", "[1][2][3]concat=n=3:v=0:a=1[a]",
         "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
         str(out)],
        check=True, capture_output=True,
    )
    return out
