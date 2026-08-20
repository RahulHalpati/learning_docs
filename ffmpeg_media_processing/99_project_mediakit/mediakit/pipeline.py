"""End-to-end: a long video in, a captioned vertical clip out.

This is the whole short-form pipeline, and it is deliberately only ~30 lines —
because every hard part already lives in a tested function. Swapping the naive
`pick_highlight` for an LLM is the one change that makes it "AI-powered".
"""
from __future__ import annotations

from pathlib import Path

from .captions import Cue, split_long_cues, write_srt
from .core import duration
from .ops import burn_captions, cut_clip, to_vertical
from .transcribe import transcribe


def pick_highlight(cues: list[Cue], *, target: float = 30.0) -> tuple[float, float]:
    """Choose the clip window. Naive: the densest `target` seconds of speech.

    Slides a window over the cues and keeps the position with the most spoken
    characters — a decent proxy for "something is happening here".

    This is the seam where an LLM goes: hand it the transcript, ask which span is
    most engaging, return those timestamps. The rest of the pipeline is unchanged.
    """
    if not cues:
        return (0.0, target)

    best, best_score = (cues[0].start, cues[0].start + target), -1.0
    for cue in cues:
        start, end = cue.start, cue.start + target
        score = sum(len(c.text) for c in cues if c.start >= start and c.end <= end)
        if score > best_score:
            best, best_score = (start, end), score
    return best


def make_clip(
    src: str | Path,
    outdir: str | Path,
    *,
    target: float = 30.0,
    vertical: bool = True,
    model_size: str = "base",
) -> dict:
    """Transcribe -> pick a highlight -> cut -> reframe -> burn captions.

    Returns the artifact paths and the chosen window, so a caller (an API job, a
    LangGraph node) can report progress without re-deriving anything.
    """
    src, outdir = Path(src), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cues = transcribe(src, model_size=model_size, workdir=outdir)
    start, end = pick_highlight(cues, target=target)
    end = min(end, duration(src))

    clip = cut_clip(src, outdir / "clip.mp4", start, end)
    if vertical:
        clip = to_vertical(clip, outdir / "clip_vertical.mp4")

    # Rebase cue timings onto the clip: the clip starts at 0, the source didn't.
    local = [
        Cue(max(0.0, c.start - start), min(end - start, c.end - start), c.text)
        for c in cues
        if c.end > start and c.start < end
    ]
    srt = write_srt(split_long_cues(local), outdir / "captions.srt")
    final = burn_captions(clip, srt, outdir / "final.mp4")

    return {
        "source": str(src),
        "window": (round(start, 2), round(end, 2)),
        "cues": len(local),
        "srt": str(srt),
        "final": str(final),
    }
