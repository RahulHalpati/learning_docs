"""The media layer: turn text into slides, narration, and a finished .mp4.

Design goal: **the pipeline always runs with zero extra installs.**

* Slides   → Pillow (rendered PNGs). Required.
* Narration→ pluggable TTS via $STUDIO_TTS. If no engine is available it falls
             back to an ffmpeg-synthesised track sized to the reading time, so
             timing/assembly still work end to end. Swap in a real voice later.
* Assembly → ffmpeg (slideshow + audio → mp4). Required.

Everything here shells out to `ffmpeg`; the only Python dependency is Pillow.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 720          # 720p 16:9; bump to 1920x1080 for real uploads
FPS = 25
WORDS_PER_MINUTE = 150             # average narration pace, used to estimate timing


# --------------------------------------------------------------------------- #
# ffmpeg helpers
# --------------------------------------------------------------------------- #
def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install it: `sudo apt install ffmpeg` "
            "(Debian/Ubuntu) or `brew install ffmpeg` (macOS)."
        )
    return exe


def _run(cmd: list[str]) -> None:
    """Run a command, raising with ffmpeg's stderr if it fails."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr[-1500:]}"
        )


def estimate_duration(text: str, *, min_seconds: float = 2.0) -> float:
    """Rough seconds to read `text` aloud at WORDS_PER_MINUTE."""
    words = max(1, len(text.split()))
    return max(min_seconds, round(words / WORDS_PER_MINUTE * 60, 2))


# --------------------------------------------------------------------------- #
# Slides (Pillow)
# --------------------------------------------------------------------------- #
def _font(size: int) -> ImageFont.FreeTypeFont:
    """A scalable font with no external file dependency (Pillow 10+)."""
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow — fixed-size bitmap fallback
        return ImageFont.load_default()


def render_slide(
    heading: str,
    subtitle: str,
    out_path: str | Path,
    *,
    index: int | None = None,
    total: int | None = None,
) -> str:
    """Render one 16:9 title/subtitle slide to a PNG and return its path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (WIDTH, HEIGHT), (14, 17, 23))         # near-black
    draw = ImageDraw.Draw(img)

    # accent bar
    draw.rectangle([0, 0, WIDTH, 10], fill=(88, 166, 255))

    # heading (wrapped, centered vertically-ish)
    h_font = _font(64)
    heading_lines = textwrap.wrap(heading, width=24) or [""]
    y = 190
    for line in heading_lines:
        w = draw.textlength(line, font=h_font)
        draw.text(((WIDTH - w) / 2, y), line, font=h_font, fill=(240, 246, 252))
        y += 78

    # subtitle
    s_font = _font(34)
    for line in textwrap.wrap(subtitle, width=52)[:4]:
        w = draw.textlength(line, font=s_font)
        draw.text(((WIDTH - w) / 2, y + 20), line, font=s_font, fill=(139, 148, 158))
        y += 46

    # footer / progress
    if index is not None and total is not None:
        f_font = _font(24)
        tag = f"{index + 1} / {total}"
        draw.text((WIDTH - 110, HEIGHT - 50), tag, font=f_font, fill=(88, 166, 255))

    img.save(out_path)
    return str(out_path)


# --------------------------------------------------------------------------- #
# Narration (pluggable TTS + offline fallback)
# --------------------------------------------------------------------------- #
def synth_narration(text: str, out_path: str | Path) -> float:
    """Synthesise narration for `text` to a .wav, returning its duration (s).

    Engine chosen by $STUDIO_TTS:
      * ``auto`` (default) — try pyttsx3, else fall back to a silent track.
      * ``pyttsx3``        — offline OS voices (needs `pip install pyttsx3`).
      * ``gtts``           — Google TTS, online (needs `pip install gTTS`).
      * ``none``           — always a silent track sized to reading time.

    The silent fallback keeps the pipeline runnable everywhere; the video is
    correctly timed, it just has no voice yet. Swap in a real engine and every
    downstream node stays identical.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    engine = os.environ.get("STUDIO_TTS", "auto").lower()

    if engine in ("auto", "pyttsx3"):
        try:
            import pyttsx3  # noqa: F401

            tts = pyttsx3.init()
            tts.save_to_file(text, str(out_path))
            tts.runAndWait()
            if out_path.exists() and out_path.stat().st_size > 0:
                return _probe_duration(out_path)
        except Exception:
            if engine == "pyttsx3":
                raise  # explicit request — surface the failure

    if engine == "gtts":
        from gtts import gTTS

        mp3 = out_path.with_suffix(".mp3")
        gTTS(text=text).save(str(mp3))
        _run([_ffmpeg(), "-y", "-i", str(mp3), str(out_path)])
        return _probe_duration(out_path)

    # Fallback: a silent track sized to the estimated reading time.
    duration = estimate_duration(text)
    _run([
        _ffmpeg(), "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(duration), str(out_path),
    ])
    return duration


def _probe_duration(path: str | Path) -> float:
    """Read an audio/video file's duration with ffprobe (falls back to estimate)."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 3.0
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return round(float(proc.stdout.strip()), 2)
    except (ValueError, AttributeError):
        return 3.0


def stitch_audio(segment_paths: list[str], out_path: str | Path) -> float:
    """Concatenate per-segment narration .wavs into one track."""
    out_path = Path(out_path)
    listing = out_path.with_suffix(".txt")
    listing.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in segment_paths))
    _run([
        _ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c", "copy", str(out_path),
    ])
    return _probe_duration(out_path)


# --------------------------------------------------------------------------- #
# Assembly (ffmpeg slideshow + audio)
# --------------------------------------------------------------------------- #
def assemble_video(
    image_paths: list[str],
    durations: list[float],
    audio_path: str | Path,
    out_path: str | Path,
) -> str:
    """Combine timed slides + narration into a single .mp4."""
    if len(image_paths) != len(durations):
        raise ValueError("image_paths and durations must be the same length")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # concat demuxer: each image shown for its duration; last one repeated (ffmpeg quirk)
    lines = []
    for img, dur in zip(image_paths, durations):
        lines.append(f"file '{Path(img).resolve()}'")
        lines.append(f"duration {dur}")
    lines.append(f"file '{Path(image_paths[-1]).resolve()}'")
    listing = out_path.with_name(out_path.stem + "_slides.txt")
    listing.write_text("\n".join(lines) + "\n")

    cmd = [
        _ffmpeg(), "-y",
        "-f", "concat", "-safe", "0", "-i", str(listing),
        "-i", str(audio_path),
        "-vf", f"fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", str(out_path),
    ]
    try:
        _run(cmd)
    except RuntimeError:
        # some ffmpeg builds lack libx264 — fall back to the always-present mpeg4
        cmd[cmd.index("libx264")] = "mpeg4"
        _run(cmd)
    return str(out_path)
