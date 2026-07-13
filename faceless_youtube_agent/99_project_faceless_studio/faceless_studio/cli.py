"""Command-line entry point.

    # offline demo (fake model + silent narration), produces a real out/<slug>/video.mp4
    STUDIO_LLM=fake python -m faceless_studio.cli "Big-O notation for beginners"

    # real local model
    STUDIO_LLM=ollama python -m faceless_studio.cli "Why RAM is faster than disk"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .graph import produce_video


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a faceless video from a topic.")
    parser.add_argument("topic", help="the topic/idea for the video")
    parser.add_argument("--niche", default="short educational explainers")
    parser.add_argument("--workdir", default="out", help="where to write artifacts")
    args = parser.parse_args(argv)

    print(f"🎬 Producing: {args.topic!r}\n", file=sys.stderr)
    state = produce_video(args.topic, niche=args.niche, workdir=args.workdir)

    print("─" * 60, file=sys.stderr)
    print(f"✅ Pipeline path: {' → '.join(state.get('log', []))}", file=sys.stderr)
    print(f"🎞️  Video:    {state.get('video_path')}", file=sys.stderr)
    print(f"📝 Title:    {state.get('title')}", file=sys.stderr)
    print(f"🏷️  Tags:     {', '.join(state.get('tags', []))}", file=sys.stderr)

    # write the upload-ready metadata next to the video
    if state.get("video_path"):
        meta_path = Path(state["video_path"]).with_name("metadata.json")
        meta_path.write_text(json.dumps({
            "title": state.get("title"),
            "description": state.get("description"),
            "tags": state.get("tags"),
        }, indent=2))
        print(f"📄 Metadata: {meta_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
