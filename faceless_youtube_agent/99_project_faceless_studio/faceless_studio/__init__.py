"""Faceless Studio — a LangGraph pipeline that turns a topic into a finished video.

    topic → research → script → voiceover → visuals → assemble → metadata → (upload)

Everything runs offline with no API key: the LLM falls back to a canned fake
model, the voiceover falls back to an ffmpeg-synthesised narration track, and
the visuals are rendered with Pillow. Real providers (Ollama/Claude/OpenAI),
real TTS (Piper/edge-tts/ElevenLabs) and real YouTube upload are one env-var or
one function call away — see the module docstrings.
"""

from .graph import build_graph, produce_video
from .state import VideoState

__all__ = ["build_graph", "produce_video", "VideoState"]
