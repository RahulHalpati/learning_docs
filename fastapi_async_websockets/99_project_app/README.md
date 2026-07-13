# Streaming AI Chat — project app

The complete app for [Module 99](../99_project_streaming_chat.md). Real-time AI chat over a WebSocket, with token-by-token streaming, conversation memory, and a stop button. Runs on a no-key **mock** backend by default, or a real **NVIDIA**/**Ollama** model.

## Files

| File | What it is |
|------|-----------|
| [`llm.py`](llm.py) | Backend abstraction — one async `stream_reply` generator over mock / NVIDIA / Ollama |
| [`main.py`](main.py) | FastAPI app: lifespan HTTP client, `/` serves the UI, `/ws/chat` bridges tokens, stop support |
| [`index.html`](index.html) | Single-file browser chat UI (WebSocket client) |
| [`test_app.py`](test_app.py) | In-process backend tests (mock mode) |
| [`requirements.txt`](requirements.txt) | Pinned, verified dependencies |

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

fastapi dev main.py            # mock backend; open http://127.0.0.1:8000
```

Real backends:

```bash
# NVIDIA hosted (free key from build.nvidia.com)
LLM_BACKEND=nvidia NVIDIA_API_KEY=nvapi-xxxxx fastapi dev main.py

# Ollama (local; first run `ollama pull llama3.2`)
LLM_BACKEND=ollama LLM_MODEL=llama3.2 fastapi dev main.py
```

## Configuration (env vars)

| Variable | Default | Meaning |
|----------|---------|---------|
| `LLM_BACKEND` | `mock` | `mock`, `nvidia`, or `ollama` |
| `LLM_MODEL` | per-backend | model name (e.g. `moonshotai/kimi-k2.6`, `llama3.2`) |
| `NVIDIA_API_KEY` | — | required when `LLM_BACKEND=nvidia` |

## Test

```bash
python test_app.py
```

Expected output (mock backend):

```
GET / -> 200 text/html; charset=utf-8 len 4772
turn1: 37 tokens, stopped=False
turn1 reply starts: "You said: 'Hello there'. This is a mock "
turn2 stopped= False
stop test: 0 tokens before end, stopped=True
ALL PROJECT TESTS PASSED
```

(The exact token count before "stop" depends on timing; `stopped=True` is the assertion that matters.)
