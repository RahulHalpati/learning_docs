"""The media operations an AI video pipeline actually needs.

Each function is one ffmpeg invocation with the flags that matter, and returns
the output path so calls chain. Nothing here is clever — the value is that the
flag choices are the *correct* ones, and each is explained in a lesson.
"""
from __future__ import annotations

import re
from pathlib import Path

from .core import duration, ffmpeg, run

# ---------------------------------------------------------------- audio


def extract_audio(src: str | Path, dst: str | Path, *, rate: int = 16000, mono: bool = True) -> Path:
    """Extract audio as PCM WAV — the format speech-to-text models want.

    16 kHz mono is what Whisper (and faster-whisper) resample to internally, so
    handing it that directly skips a conversion and shrinks the file ~6x vs 44.1k
    stereo. `-vn` drops the video stream.
    """
    args = ["-i", str(src), "-vn", "-ar", str(rate)]
    if mono:
        args += ["-ac", "1"]
    args += ["-c:a", "pcm_s16le", str(dst)]
    ffmpeg(args)
    return Path(dst)


# ---------------------------------------------------------------- cutting


def cut_clip(
    src: str | Path,
    dst: str | Path,
    start: float,
    end: float,
    *,
    accurate: bool = True,
) -> Path:
    """Cut [start, end) out of `src`.

    accurate=True re-encodes: the cut lands exactly on the requested timestamps.
    accurate=False stream-copies: ~5x faster, but the cut snaps to the nearest
    keyframe, so you get *approximately* the range you asked for.

    For clip extraction where the first frame must be right, keep accurate=True.
    """
    args = ["-ss", f"{start}", "-to", f"{end}", "-i", str(src)]
    if accurate:
        args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac"]
    else:
        args += ["-c", "copy"]
    args += [str(dst)]
    ffmpeg(args)
    return Path(dst)


def concat(parts: list[str | Path], dst: str | Path, *, workdir: str | Path | None = None) -> Path:
    """Join clips that share a codec/resolution, using the concat demuxer.

    Fast (stream copy) but strict: mismatched codecs or dimensions produce a
    corrupt or rejected output. Re-encode the parts to a common format first if
    they come from different sources.
    """
    parts = [Path(p).resolve() for p in parts]
    if not parts:
        raise ValueError("concat() needs at least one part")
    listfile = Path(workdir or Path(dst).parent) / "_concat.txt"
    # Single quotes are the demuxer's escape; a literal quote in a filename breaks it.
    listfile.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(dst)])
    listfile.unlink(missing_ok=True)
    return Path(dst)


# ---------------------------------------------------------------- framing


def to_vertical(src: str | Path, dst: str | Path, *, width: int = 1080, height: int = 1920) -> Path:
    """Reframe landscape video to 9:16 for Shorts/Reels/TikTok.

    Centre-crops to the target aspect, then scales. Naive but predictable — the
    subject-tracking version is a later upgrade, not a prerequisite.
    """
    vf = f"crop=ih*{width}/{height}:ih,scale={width}:{height}"
    ffmpeg(["-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", "23",
            "-c:a", "copy", str(dst)])
    return Path(dst)


def thumbnail(src: str | Path, dst: str | Path, *, at: float | None = None) -> Path:
    """Grab a single frame as an image. Defaults to the midpoint."""
    at = duration(src) / 2 if at is None else at
    ffmpeg(["-ss", f"{at}", "-i", str(src), "-frames:v", "1", str(dst)])
    return Path(dst)


# ---------------------------------------------------------------- captions


def burn_captions(
    src: str | Path,
    srt: str | Path,
    dst: str | Path,
    *,
    font_size: int = 24,
    margin_v: int = 40,
) -> Path:
    """Burn subtitles permanently into the pixels.

    Social platforms strip soft subtitle tracks and most viewers watch muted, so
    burned-in is the default for short-form. `_escape_filter_path` handles the
    filter-argument quoting that trips everyone up on real paths.
    """
    style = f"FontSize={font_size},MarginV={margin_v},PrimaryColour=&H00FFFFFF,BorderStyle=3"
    vf = f"subtitles={_escape_filter_path(srt)}:force_style='{style}'"
    ffmpeg(["-i", str(src), "-vf", vf, "-c:a", "copy", str(dst)])
    return Path(dst)


def _escape_filter_path(path: str | Path) -> str:
    """Quote a path for use *inside* a filtergraph argument.

    Filtergraphs use ':' as an option separator and ',' to chain filters, so a
    path containing either breaks parsing — and on Windows every path has a
    'C:' in it. Backslash-escaping those inside single quotes is the fix.
    """
    p = str(path).replace("\\", "/")
    p = p.replace("'", r"\'").replace(":", r"\:").replace(",", r"\,")
    return f"'{p}'"


# ---------------------------------------------------------------- analysis

_SILENCE_START = re.compile(r"silence_start:\s*([\d.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*([\d.]+)")


def detect_silence(src: str | Path, *, noise_db: int = -35, min_dur: float = 0.5) -> list[tuple[float, float]]:
    """Return [(start, end)] of silent stretches — the cheap way to find cut points.

    Runs the `silencedetect` filter with a null output: no file is written, we
    only parse what the filter logs to stderr. Raising `noise_db` (toward 0)
    treats quieter audio as silence; lower it for noisy recordings.
    """
    from .core import _which  # local: keeps the module import-light
    import subprocess

    proc = subprocess.run(
        [_which("ffmpeg"), "-hide_banner", "-i", str(src),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    log = proc.stderr
    starts = [float(m) for m in _SILENCE_START.findall(log)]
    ends = [float(m) for m in _SILENCE_END.findall(log)]
    # A trailing silence that runs to EOF logs a start with no end — close it.
    if len(starts) > len(ends):
        ends.append(duration(src))
    return list(zip(starts, ends))


def speech_segments(src: str | Path, **kwargs) -> list[tuple[float, float]]:
    """Invert detect_silence(): the stretches that actually contain sound."""
    total = duration(src)
    segments, cursor = [], 0.0
    for start, end in detect_silence(src, **kwargs):
        if start - cursor > 0.05:
            segments.append((round(cursor, 3), round(start, 3)))
        cursor = end
    if total - cursor > 0.05:
        segments.append((round(cursor, 3), round(total, 3)))
    return segments
