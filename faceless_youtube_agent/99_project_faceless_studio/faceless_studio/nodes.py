"""The pipeline nodes. Each is a plain function: read state → do one job → return
only the keys it changed. LLM-backed nodes take an `llm`; media nodes take a
`workdir`. They are bound to their dependencies in graph.py with functools.partial.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from . import media
from .state import Segment, VideoState


def _ask(llm: BaseChatModel, system: str, human: str) -> str:
    """One-shot chat call → plain text. Works with real and fake models alike."""
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    return (resp.content or "").strip()


# --------------------------------------------------------------------------- #
# 1. Researcher — turn a bare topic into a hook + angle + key points
# --------------------------------------------------------------------------- #
def topic_researcher(state: VideoState, *, llm: BaseChatModel) -> dict:
    niche = state.get("niche", "short educational explainers")
    system = (
        "You are a YouTube content researcher for a faceless channel. "
        f"The niche is: {niche}. Be concrete and retention-focused."
    )
    human = (
        f"Topic: {state['topic']}\n\n"
        "Return exactly this shape:\n"
        "HOOK: <one punchy opening line>\n"
        "ANGLE: <the specific angle in one sentence>\n"
        "POINTS:\n- <point 1>\n- <point 2>\n- <point 3>"
    )
    research = _ask(llm, system, human)

    hook_match = re.search(r"HOOK:\s*(.+)", research)
    hook = hook_match.group(1).strip() if hook_match else state["topic"]
    return {"research": research, "hook": hook, "log": ["researcher"]}


# --------------------------------------------------------------------------- #
# 2. Scriptwriter — turn the research into narrated segments
# --------------------------------------------------------------------------- #
def script_writer(state: VideoState, *, llm: BaseChatModel) -> dict:
    system = (
        "You are a scriptwriter for short faceless YouTube videos. Write tight, "
        "spoken-word narration — no stage directions, no markdown. 5-8 segments."
    )
    human = (
        f"Hook: {state.get('hook', '')}\n"
        f"Research:\n{state.get('research', '')}\n\n"
        "Return a JSON array. Each item: "
        '{"heading": "<slide title, <=4 words>", '
        '"narration": "<1-3 spoken sentences>", '
        '"visual_hint": "<how the slide should look>"}. '
        "Return ONLY the JSON array."
    )
    raw = _ask(llm, system, human)
    segments = _parse_segments(raw, state)
    return {"segments": segments, "log": ["scriptwriter"]}


def _parse_segments(raw: str, state: VideoState) -> list[Segment]:
    """Parse the LLM's JSON leniently; degrade gracefully if it isn't valid JSON."""
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            segs = [
                Segment(
                    heading=str(item.get("heading", "")).strip()[:60] or "Slide",
                    narration=str(item.get("narration", "")).strip(),
                    visual_hint=str(item.get("visual_hint", "")).strip(),
                )
                for item in data
                if str(item.get("narration", "")).strip()
            ]
            if segs:
                return segs
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    # Fallback: one segment for the hook, one per non-empty line of narration text.
    lines = [ln.strip("-• ").strip() for ln in raw.splitlines() if ln.strip()]
    segs = [Segment(heading="Intro", narration=state.get("hook", state["topic"]),
                    visual_hint="title card")]
    for i, ln in enumerate(lines[:6], start=1):
        segs.append(Segment(heading=f"Point {i}", narration=ln, visual_hint="text slide"))
    return segs


# --------------------------------------------------------------------------- #
# 3. Voiceover — synthesise narration per segment, then stitch one track
# --------------------------------------------------------------------------- #
def voiceover(state: VideoState, *, workdir: Path) -> dict:
    audio_dir = Path(workdir) / "audio"
    segments = [dict(s) for s in state["segments"]]
    seg_paths = []
    for i, seg in enumerate(segments):
        path = audio_dir / f"seg_{i:02d}.wav"
        dur = media.synth_narration(seg["narration"], path)
        seg["audio_path"] = str(path)
        seg["duration"] = dur
        seg_paths.append(str(path))

    full = Path(workdir) / "narration.wav"
    media.stitch_audio(seg_paths, full)
    return {"segments": segments, "audio_path": str(full), "log": ["voiceover"]}


# --------------------------------------------------------------------------- #
# 4. Visuals — render one slide per segment
# --------------------------------------------------------------------------- #
def visuals(state: VideoState, *, workdir: Path) -> dict:
    img_dir = Path(workdir) / "slides"
    segments = [dict(s) for s in state["segments"]]
    total = len(segments)
    paths = []
    for i, seg in enumerate(segments):
        path = img_dir / f"slide_{i:02d}.png"
        media.render_slide(
            seg["heading"], seg.get("visual_hint", ""), path, index=i, total=total
        )
        seg["image_path"] = str(path)
        paths.append(str(path))
    return {"segments": segments, "image_paths": paths, "log": ["visuals"]}


# --------------------------------------------------------------------------- #
# 5. Assembler — slides + narration → final .mp4
# --------------------------------------------------------------------------- #
def assembler(state: VideoState, *, workdir: Path) -> dict:
    segments = state["segments"]
    durations = [float(s.get("duration") or media.estimate_duration(s["narration"]))
                 for s in segments]
    out = Path(workdir) / "video.mp4"
    media.assemble_video(state["image_paths"], durations, state["audio_path"], out)
    return {"video_path": str(out), "log": ["assembler"]}


# --------------------------------------------------------------------------- #
# 6. Metadata — SEO title, description with chapters, tags
# --------------------------------------------------------------------------- #
def metadata(state: VideoState, *, llm: BaseChatModel) -> dict:
    system = (
        "You are a YouTube SEO assistant. Write a click-worthy but honest title "
        "(<=70 chars), a 2-3 sentence description, and comma-separated tags."
    )
    human = (
        f"Topic: {state['topic']}\nResearch:\n{state.get('research', '')}\n\n"
        "Return exactly:\nTITLE: ...\nDESCRIPTION: ...\nTAGS: tag1, tag2, tag3"
    )
    raw = _ask(llm, system, human)

    title = _field(raw, "TITLE") or state["topic"]
    description = _field(raw, "DESCRIPTION") or ""
    tags_line = _field(raw, "TAGS") or ""
    tags = [t.strip() for t in tags_line.split(",") if t.strip()]

    # auto-append chapter markers from segment durations (YouTube reads these)
    chapters, t = [], 0.0
    for seg in state.get("segments", []):
        mm, ss = divmod(int(t), 60)
        chapters.append(f"{mm:02d}:{ss:02d} {seg['heading']}")
        t += float(seg.get("duration") or 0)
    if chapters:
        description = description + "\n\nChapters:\n" + "\n".join(chapters)

    return {"title": title, "description": description, "tags": tags,
            "log": ["metadata"]}


def _field(text: str, key: str) -> str:
    m = re.search(rf"{key}:\s*(.+)", text)
    return m.group(1).strip() if m else ""
