"""The shared state that flows through every node in the video pipeline.

In LangGraph, all nodes read from and write to one shared state object. Each
node returns a dict of *only the keys it changes*; LangGraph merges that into
the running state. `log` uses a reducer so every node can append to it without
overwriting what previous nodes wrote.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class Segment(TypedDict, total=False):
    """One beat of the video: a slide + the narration spoken over it."""
    heading: str          # short on-screen title for the slide
    narration: str        # what the voiceover says over this slide
    visual_hint: str      # a note for how the slide/B-roll should look
    image_path: str       # filled in by the visuals node
    audio_path: str       # filled in by the voiceover node (per-segment)
    duration: float       # seconds this segment runs (from the audio length)


class VideoState(TypedDict, total=False):
    # --- input ---
    topic: str                    # the raw topic/idea the user hands in
    niche: str                    # channel niche, steers tone (e.g. "tech explainers")

    # --- produced by the nodes, in order ---
    research: str                 # researcher: hook + angle + key points (raw text)
    hook: str                     # researcher: the first spoken line (retention!)
    segments: list[Segment]       # scriptwriter fills narration; later nodes enrich

    audio_path: str               # voiceover: the full stitched narration track
    image_paths: list[str]        # visuals: one rendered slide per segment
    video_path: str               # assembler: the final .mp4

    title: str                    # metadata: SEO title
    description: str              # metadata: description + chapters
    tags: list[str]               # metadata: search tags

    # --- human-in-the-loop gate ---
    approved: bool                # set True to allow publishing

    # --- observability ---
    log: Annotated[list[str], operator.add]   # each node appends its name
