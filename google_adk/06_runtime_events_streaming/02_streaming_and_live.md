# 06-2 · Streaming & Live

> **Level:** Intermediate · **Prerequisites:** [06-1 · Runners & events](01_runners_and_events.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0; Live API needs Gemini Live + audio, not offline)

## Why this matters

For a responsive UI you don't wait for the whole answer — you show tokens as they arrive. ADK streams via **partial events**. And for voice/video assistants, the **Live API** provides a bidirectional audio/video stream. Knowing what's offline-friendly (token streaming) vs cloud-only (Live) keeps expectations straight.

---

## Token streaming via partial events

Enable streaming and `run_async` yields `partial=True` events as the model produces text, then a final consolidated event. Set it through a `RunConfig`:

```python
from google.adk.agents.run_config import RunConfig, StreamingMode

# runner.run_async(..., run_config=RunConfig(streaming_mode=StreamingMode.SSE))
#
# async for event in runner.run_async(..., run_config=...):
#     if event.partial:                     # incremental chunk
#         print(event.content.parts[0].text, end="", flush=True)
#     elif event.is_final_response():
#         print()                           # final, consolidated
```

`event.partial` distinguishes a streaming chunk from the final message. This is the ADK analog of LangGraph's `stream_mode="messages"` ([langgraph 02-2](../../langgraph/02_execution_model/02_streaming.md)). With a streaming-capable model you get token-by-token; the exact chunking depends on the model/provider.

> **Note:** streaming behavior varies by model backend. The *API* (`RunConfig(streaming_mode=...)`, `event.partial`) is stable; whether a given local model streams token-by-token depends on its LiteLLM integration. The `adk web` UI (06-3) shows streaming visually out of the box.

---

## The Live API (bidirectional audio/video)

ADK supports Gemini's **Live API** for real-time, bidirectional conversations — the agent listens to streamed audio/video and responds with streamed audio while the user is still talking (barge-in, interruptions). This powers voice assistants.

```python
# Conceptual — Live needs a Gemini Live model + an audio transport:
# from google.adk.agents.run_config import RunConfig, StreamingMode
# run_config = RunConfig(streaming_mode=StreamingMode.BIDI, response_modalities=["AUDIO"])
# runner.run_live(...)   # a live, bidirectional session
```

> ⚠️ **Not offline.** The Live API requires a Gemini Live-capable model and real audio I/O — it can't run on local Ollama or in this course's offline setup. It's here so you know it exists and when to reach for it (voice/video agents); text streaming above is the part you can run locally.

---

## What's offline vs cloud

| Feature | Offline? |
|---------|:---:|
| Event iteration (`run_async`) | ✅ |
| Token streaming (`partial` events) | ✅ (model-dependent chunking) |
| Live API (audio/video, barge-in) | ❌ Gemini Live + audio only |

---

## Recap & next

- ✅ Streaming yields `partial=True` events before the final; enable via `RunConfig(streaming_mode=...)`.
- ✅ `event.partial` separates chunks from the final message (like LangGraph's `messages` mode).
- ✅ The **Live API** is bidirectional audio/video for voice agents — cloud-only, not offline.
- ✅ Self-check: which event field tells you a chunk is a streaming fragment vs the final answer?

→ Next: **[06-3 · API server & clients](03_api_server_and_clients.md)**

## Exercises

1. With an Ollama agent, run with `RunConfig(streaming_mode=StreamingMode.SSE)` and print `partial` chunks as they arrive.

<details>
<summary>Solution</summary>

Pass `run_config=RunConfig(streaming_mode=StreamingMode.SSE)` to `run_async` and, in the loop, `print(event.content.parts[0].text, end="")` when `event.partial`. Chunk granularity depends on the model backend.
</details>
