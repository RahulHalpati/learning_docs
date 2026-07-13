# 01-3 · Environment & providers

> **Level:** Beginner · **Time:** 20 min · **Verified:** Python 3.10.12, langgraph 1.1.10, ffmpeg 4.4.2

Let's get everything installed and run the pipeline once, offline, to prove the
setup works before you learn how it works.

---

## 1. System dependency: ffmpeg

ffmpeg is the only non-Python requirement. It renders the video.

```bash
# Debian/Ubuntu
sudo apt install ffmpeg
# macOS
brew install ffmpeg

ffmpeg -version   # confirm it's on PATH
```

```
ffmpeg version 4.4.2-0ubuntu0.22.04.1 Copyright (c) 2000-2021 the FFmpeg developers
```

---

## 2. Python packages

```bash
cd 99_project_faceless_studio
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The **required** core is tiny: `langgraph`, `langchain-core`, `Pillow`. TTS
engines and YouTube upload libraries are commented out in `requirements.txt` —
you add them only when you want those upgrades.

---

## 3. The provider switch

Every LLM-backed node gets its model from one place — `providers.py` — controlled
by the `STUDIO_LLM` env var. This is the same fall-back pattern the
[Proposal Agent](../../langgraph_proposal_agent/) uses:

| `STUDIO_LLM` | Model | Needs |
|---|---|---|
| `fake` | canned replies | nothing — used by tests |
| `ollama` *(default)* | local `qwen2:7b` | [Ollama](https://ollama.com) running |
| `anthropic` | Claude | `ANTHROPIC_API_KEY` + `langchain-anthropic` |
| `openai` | GPT / compatible | `OPENAI_API_KEY` + `langchain-openai` |

If a provider can't load (missing package or key), it **silently falls back to
`fake`** so the pipeline always runs. No dead ends.

```python
# providers.py — the important bit
provider = os.environ.get("STUDIO_LLM", "ollama").lower()
if provider == "ollama":
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(model=os.environ.get("OLLAMA_MODEL", "qwen2:7b"))
    except Exception:
        provider = "fake"
...
return GenericFakeChatModel(messages=iter(_FAKE_REPLIES))
```

### Optional: local Ollama for real generation

```bash
# install from https://ollama.com, then:
ollama pull qwen2:7b
ollama list          # confirm it's there
```

---

## 4. Run it once (offline)

```bash
STUDIO_LLM=fake python -m faceless_studio.cli "Big-O notation for beginners"
```

Real output from the verified environment:

```
🎬 Producing: 'Big-O notation for beginners'
────────────────────────────────────────────────────────────
✅ Pipeline path: researcher → scriptwriter → voiceover → visuals → assembler → metadata
🎞️  Video:    out/big-o-notation-for-beginners/video.mp4
📝 Title:    Why Your Code Slows Down (Big-O Explained in 3 Minutes)
🏷️  Tags:     big o, algorithms, time complexity, coding, computer science, programming
```

Confirm the file is a real video:

```bash
ffprobe out/big-o-notation-for-beginners/video.mp4
# → Video: h264 1280x720 ... Audio: aac ... Duration: 00:00:23
```

Then run the tests (also fully offline):

```bash
python -m pytest -q
# 7 passed
```

If both worked, your environment is correct and you can focus on *learning*.

---

## 5. Try the real local model (optional)

```bash
STUDIO_LLM=ollama python -m faceless_studio.cli "Why RAM is faster than a hard disk"
```

This was run in the verified environment and produced a real `.mp4` — with
`qwen2:7b` writing the segments and chapters. One thing to notice: a small local
model doesn't always follow the `TITLE:`/`TAGS:` format exactly, so the metadata
node's **fallback** kicks in (it uses the topic as the title). That's not a bug —
it's why every parser in this course degrades gracefully. More on that in
[02-7](../02_building_the_nodes/07_metadata.md).

---

## Recap

- **ffmpeg** is the one system dependency; the Python core is just
  `langgraph` + `langchain-core` + `Pillow`.
- `STUDIO_LLM` picks the model; anything that fails to load **falls back to a fake
  model**, so the pipeline never dead-ends.
- You've produced a real `.mp4` and passed the tests offline — setup verified.

## Self-check

1. What happens if you set `STUDIO_LLM=openai` but haven't installed
   `langchain-openai`?
2. What is the only non-pip dependency, and what does it do?

<details>
<summary>Answers</summary>

1. The `import` fails inside the `try`, `provider` is set to `"fake"`, and the
   canned model is used — the pipeline still runs.
2. **ffmpeg** — it stitches the timed slides and narration into the final `.mp4`.

</details>

---

**Next → [01-4 · LangGraph refresher](04_langgraph_refresher.md)**
