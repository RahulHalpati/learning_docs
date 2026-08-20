"""SRT subtitles: write them, read them, split them for short-form video.

This is the bridge between a speech-to-text model and ffmpeg. Transcribers hand
you `(start, end, text)`; `burn_captions()` wants an SRT file. That's this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cue:
    start: float
    end: float
    text: str


def timestamp(seconds: float) -> str:
    """Seconds -> SRT timestamp `HH:MM:SS,mmm` (comma before ms, not a period)."""
    if seconds < 0:
        raise ValueError(f"negative timestamp: {seconds}")
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues: list[Cue], dst: str | Path) -> Path:
    """Write cues to an SRT file. Indices are 1-based and must be contiguous."""
    blocks = [
        f"{i}\n{timestamp(c.start)} --> {timestamp(c.end)}\n{c.text.strip()}\n"
        for i, c in enumerate(cues, start=1)
    ]
    path = Path(dst)
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path


def from_segments(segments) -> list[Cue]:
    """Adapt a transcriber's output to Cues.

    Accepts faster-whisper segment objects (attributes) or plain dicts, so the
    rest of the pipeline doesn't care which transcriber produced them.
    """
    cues = []
    for s in segments:
        if isinstance(s, dict):
            cues.append(Cue(float(s["start"]), float(s["end"]), str(s["text"])))
        else:
            cues.append(Cue(float(s.start), float(s.end), str(s.text)))
    return cues


def split_long_cues(cues: list[Cue], *, max_chars: int = 42) -> list[Cue]:
    """Break wordy cues into readable chunks, splitting their time proportionally.

    Whisper emits sentence-length segments; a 90-character line is unreadable on a
    phone. 42 chars/line is the broadcast-captioning convention. Time is divided by
    word count, which is approximate but visually fine at this length.
    """
    out: list[Cue] = []
    for cue in cues:
        words = cue.text.split()
        if len(cue.text) <= max_chars or not words:
            out.append(cue)
            continue

        lines, current = [], ""
        for word in words:
            if current and len(current) + 1 + len(word) > max_chars:
                lines.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current:
            lines.append(current)

        span = cue.end - cue.start
        total_words = len(words)
        cursor = cue.start
        for line in lines:
            share = span * (len(line.split()) / total_words)
            out.append(Cue(round(cursor, 3), round(cursor + share, 3), line))
            cursor += share
    return out
