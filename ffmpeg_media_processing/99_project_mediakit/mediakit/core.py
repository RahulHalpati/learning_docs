"""ffmpeg plumbing: locate the binary, run commands, surface real errors.

Every other module in mediakit goes through `run()`. Centralising it means one
place handles the two things that always bite: ffmpeg not being installed, and
ffmpeg failing with its explanation buried in stderr.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    """Raised when ffmpeg/ffprobe exits non-zero. Carries ffmpeg's own stderr."""


def _which(binary: str) -> str:
    exe = shutil.which(binary)
    if exe is None:
        raise FFmpegError(
            f"{binary} not found on PATH. Install it: "
            "`sudo apt install ffmpeg` (Debian/Ubuntu) or `brew install ffmpeg` (macOS)."
        )
    return exe


def run(args: list[str], *, binary: str = "ffmpeg") -> str:
    """Run ffmpeg/ffprobe. Returns stdout; raises FFmpegError with stderr on failure.

    ffmpeg writes its diagnostics to stderr and exits non-zero on failure — so a
    bare subprocess call fails silently-ish. This surfaces the real reason.
    """
    cmd = [_which(binary), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(
            f"{binary} failed (exit {proc.returncode})\n"
            f"command: {' '.join(cmd)}\n\n{proc.stderr.strip()}"
        )
    return proc.stdout


def ffmpeg(args: list[str], *, overwrite: bool = True) -> str:
    """Run ffmpeg with sane defaults: quiet, and -y so it never blocks on a prompt."""
    base = ["-hide_banner", "-loglevel", "error"]
    if overwrite:
        base.append("-y")
    return run([*base, *args])


def probe(path: str | Path) -> dict:
    """Return {duration, size, format, streams:[...]} for a media file."""
    out = run(
        ["-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        binary="ffprobe",
    )
    data = json.loads(out)
    fmt = data.get("format", {})
    return {
        "duration": float(fmt.get("duration", 0.0)),
        "size": int(fmt.get("size", 0)),
        "format": fmt.get("format_name", ""),
        "streams": [
            {
                "type": s.get("codec_type"),
                "codec": s.get("codec_name"),
                "width": s.get("width"),
                "height": s.get("height"),
                "sample_rate": s.get("sample_rate"),
                "channels": s.get("channels"),
            }
            for s in data.get("streams", [])
        ],
    }


def duration(path: str | Path) -> float:
    """Just the duration in seconds — the most-used probe result."""
    return probe(path)["duration"]


def has_audio(path: str | Path) -> bool:
    return any(s["type"] == "audio" for s in probe(path)["streams"])
