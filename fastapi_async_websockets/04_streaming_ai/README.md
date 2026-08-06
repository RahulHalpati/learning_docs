# Section 04 · Streaming AI

> **Prerequisites:** [Section 03 · WebSockets](../03_websockets/README.md), [Section 01.03 · httpx](../01_async_python/03_async_io_httpx.md).
> **Time:** ~2–3 hours.

This is where everything converges. You'll learn how an LLM API **streams** its answer (the SSE format), consume that stream the async way with `httpx`, and then **bridge** it onto a WebSocket so tokens flow all the way to the browser as they're generated. After this section you'll have every piece the capstone project assembles.

## The backend we target

The project uses an **OpenAI-compatible** chat endpoint. Two interchangeable options, same request/response shape:

- **NVIDIA's free hosted API** — `https://integrate.api.nvidia.com/v1/chat/completions`, Bearer-token auth, model e.g. `moonshotai/kimi-k2.6`. Needs a free API key.
- **Ollama** (local) — `http://localhost:11434/v1/chat/completions`, no key, runs models on your machine.

Because both speak the same protocol, one code path covers them. And because neither can run in this course's sandbox, every streaming example is **verified against a local mock SSE server** that emits the exact same wire format — then shown wired to the real endpoints.

## Modules

| # | Module | You'll learn |
|---|--------|--------------|
| 01 | [Consume LLM token streams (SSE)](01_llm_streaming_sse.md) | The SSE wire format; `httpx` streaming; an async token generator |
| 02 | [Bridge SSE → WebSocket](02_bridge_sse_to_ws.md) | Push each token over a WebSocket as it arrives; handle stop/disconnect |

→ Start: **[01 · Consume LLM token streams (SSE)](01_llm_streaming_sse.md)**
