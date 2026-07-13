# 99 · Capstone — Faceless Studio

A complete, runnable LangGraph pipeline that turns a topic into a finished
`.mp4` + upload-ready metadata. This is the finished version of everything the
course builds.

```
topic → researcher → scriptwriter → voiceover → visuals → assembler → metadata → mp4
                          └── (optional human review gate) ──┘
```

---

## Layout

```
99_project_faceless_studio/
├── faceless_studio/
│   ├── state.py        # VideoState + Segment  (the shared state)
│   ├── providers.py    # get_chat_model: ollama / anthropic / openai / fake
│   ├── media.py        # Pillow slides + ffmpeg assembly + pluggable TTS
│   ├── nodes.py        # the six pipeline nodes
│   ├── graph.py        # build_graph + produce_video
│   ├── cli.py          # `python -m faceless_studio.cli "<topic>"`
│   └── publish.py      # YouTube Data API v3 upload (needs OAuth; not offline)
├── data/topics/sample_topics.txt
├── tests/              # 7 offline tests (fake model, no network)
└── requirements.txt
```

---

## Quick start (offline, zero API key)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # + system ffmpeg: sudo apt install ffmpeg

# offline demo — canned model + silent narration → a REAL out/<slug>/video.mp4
STUDIO_LLM=fake python -m faceless_studio.cli "Big-O notation for beginners"

# all tests, fully offline
python -m pytest -q

# real local model (needs: ollama pull qwen2:7b)
STUDIO_LLM=ollama python -m faceless_studio.cli "Why RAM is faster than a hard disk"
```

### Verified output

Run in the course's environment (Python 3.10.12, langgraph 1.1.10, ffmpeg 4.4.2):

```
🎬 Producing: 'Big-O notation for beginners'
✅ Pipeline path: researcher → scriptwriter → voiceover → visuals → assembler → metadata
🎞️  Video:    out/big-o-notation-for-beginners/video.mp4   (h264 1280x720, aac, 23.24s)
📝 Title:    Why Your Code Slows Down (Big-O Explained in 3 Minutes)
```

```
$ python -m pytest -q
7 passed
```

---

## Configuration

| Env var | Default | Options |
|---|---|---|
| `STUDIO_LLM` | `ollama` | `fake`, `ollama`, `anthropic`, `openai` |
| `OLLAMA_MODEL` | `qwen2:7b` | any local Ollama model |
| `STUDIO_TTS` | `auto` | `auto`, `pyttsx3`, `gtts`, `none` |
| `LANGSMITH_TRACING` | *(off)* | `true` (+ `LANGSMITH_API_KEY`) for tracing |

Anything that can't load falls back to a safe default — the pipeline always runs.

---

## What's real vs. what's a stub

| Part | Offline default (runs now) | Real upgrade |
|---|---|---|
| LLM | fake / local Ollama | Claude, OpenAI |
| Voiceover | ffmpeg silent track sized to reading time | pyttsx3 / edge-tts / Piper / ElevenLabs |
| Visuals | Pillow slides | AI images (SDXL) / stock B-roll |
| Video | real h264/aac `.mp4` via ffmpeg | same, at 1080p/4K |
| Upload | not run (needs OAuth) | YouTube Data API v3 (`publish.py`) |

Every upgrade is a **single-node change** — the graph, state, and other nodes stay
identical. That's the design lesson of the whole course.

---

## Extending it

Ideas, roughly in order of value:

1. **Real voice** — add an `edge-tts` branch to `media.synth_narration` (~5 lines).
2. **Real visuals** — swap `render_slide` for AI images or Pexels B-roll.
3. **Review loop** — add a `reviewer` node + conditional edge back to the scriptwriter.
4. **Quality gate** — a `quality` node that flags weak drafts (see [05-1](../05_quality_and_shipping/01_cost_observability_quality.md)).
5. **Serve it** — wrap `produce_video` in a FastAPI endpoint (see the
   [FastAPI course](../../fastapi_async_websockets/)).

→ Full walkthrough starts at the course **[README](../README.md)** → **[00 · Introduction](../00_introduction.md)**.
