"""CLI: `python -m mediakit <command>`."""
from __future__ import annotations

import argparse
import json
import sys

from .core import FFmpegError, probe
from .ops import extract_audio, cut_clip, detect_silence, to_vertical
from .pipeline import make_clip
from .transcribe import is_available


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mediakit", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="show streams and duration")
    p.add_argument("src")

    p = sub.add_parser("audio", help="extract 16k mono wav for speech-to-text")
    p.add_argument("src"); p.add_argument("dst")

    p = sub.add_parser("cut", help="cut an accurate clip")
    p.add_argument("src"); p.add_argument("dst")
    p.add_argument("start", type=float); p.add_argument("end", type=float)

    p = sub.add_parser("vertical", help="reframe to 9:16")
    p.add_argument("src"); p.add_argument("dst")

    p = sub.add_parser("silence", help="list silent stretches")
    p.add_argument("src"); p.add_argument("--noise", type=int, default=-35)

    p = sub.add_parser("clip", help="full pipeline: transcribe, cut, caption")
    p.add_argument("src"); p.add_argument("outdir")
    p.add_argument("--target", type=float, default=30.0)

    args = parser.parse_args(argv)

    try:
        if args.cmd == "probe":
            print(json.dumps(probe(args.src), indent=2))
        elif args.cmd == "audio":
            print(extract_audio(args.src, args.dst))
        elif args.cmd == "cut":
            print(cut_clip(args.src, args.dst, args.start, args.end))
        elif args.cmd == "vertical":
            print(to_vertical(args.src, args.dst))
        elif args.cmd == "silence":
            for start, end in detect_silence(args.src, noise_db=args.noise):
                print(f"{start:8.3f} -> {end:8.3f}  ({end - start:.3f}s)")
        elif args.cmd == "clip":
            if not is_available():
                print("note: faster-whisper not installed — using placeholder "
                      "captions with real timings.", file=sys.stderr)
            print(json.dumps(make_clip(args.src, args.outdir, target=args.target), indent=2))
    except FFmpegError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
