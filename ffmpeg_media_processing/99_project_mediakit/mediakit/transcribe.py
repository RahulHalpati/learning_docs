"""Speech-to-text -> Cues, with an offline fallback so the pipeline always runs.

faster-whisper is the default because it is genuinely free: MIT-licensed, models
included, runs locally on CPU. No API key, no per-minute billing. It is a heavy
optional install (~1 GB with a model), so this module degrades gracefully — the
rest of mediakit is testable without it.
"""
from __future__ import annotations

from pathlib import Path

from .captions import Cue
from .ops import extract_audio, speech_segments


def is_available() -> bool:
    """True if faster-whisper is installed."""
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def transcribe(
    media: str | Path,
    *,
    model_size: str = "base",
    language: str | None = None,
    compute_type: str = "int8",
    workdir: str | Path | None = None,
) -> list[Cue]:
    """Transcribe media to timed Cues.

    Falls back to silence-based segmentation with placeholder text when
    faster-whisper isn't installed — timings are real, words are not. That keeps
    the cut/caption/render path exercisable offline and in CI.

    `compute_type="int8"` is the CPU sweet spot: roughly 4x faster than float32
    with negligible accuracy loss on the small/base models.
    """
    media = Path(media)
    if not is_available():
        return _placeholder_cues(media)

    from faster_whisper import WhisperModel

    workdir = Path(workdir or media.parent)
    wav = extract_audio(media, workdir / f"{media.stem}.16k.wav")

    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    segments, _info = model.transcribe(str(wav), language=language, vad_filter=True)
    return [Cue(float(s.start), float(s.end), s.text.strip()) for s in segments]


def _placeholder_cues(media: Path) -> list[Cue]:
    """Real timings from silence detection, stub text. Offline development aid."""
    return [
        Cue(start, end, f"[segment {i}]")
        for i, (start, end) in enumerate(speech_segments(media), start=1)
    ]
