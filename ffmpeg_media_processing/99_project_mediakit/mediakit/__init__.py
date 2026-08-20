"""mediakit — the ffmpeg toolkit this course builds.

Every function here is one lesson's worth of ffmpeg knowledge, wrapped so the
rest of your application never builds a command line by hand.
"""
from .captions import Cue, from_segments, split_long_cues, timestamp, write_srt
from .core import FFmpegError, duration, ffmpeg, has_audio, probe, run
from .ops import (
    burn_captions,
    concat,
    cut_clip,
    detect_silence,
    extract_audio,
    speech_segments,
    thumbnail,
    to_vertical,
)

__all__ = [
    "FFmpegError", "run", "ffmpeg", "probe", "duration", "has_audio",
    "extract_audio", "cut_clip", "concat", "to_vertical", "thumbnail",
    "burn_captions", "detect_silence", "speech_segments",
    "Cue", "write_srt", "from_segments", "split_long_cues", "timestamp",
]
