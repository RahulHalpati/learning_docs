# 01: Consume LLM token streams (SSE)

> **Level:** Intermediate · **Prerequisites:** [Section 01.03 · httpx](../01_async_python/03_async_io_httpx.md), [Section 01.02 · async generators](../01_async_python/02_async_await.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-03 (httpx 0.28.1; against a local mock SSE server)

## Why this matters

When you ask an LLM with `"stream": true`, it doesn't send one big JSON reply — it sends a **stream of tiny chunks**, one per token, using a format called **Server-Sent Events (SSE)**. To get the typing effect, you must read that stream and emit each token as it lands. This module decodes the SSE format and builds an **async token generator** you'll feed straight into a WebSocket next module.

## Concept: what the stream looks like on the wire

With streaming on, an OpenAI-compatible endpoint responds with `Content-Type: text/event-stream` and a sequence of lines like this (one **event** per token, events separated by a blank line):

```
data: {"choices":[{"delta":{"content":"Hello"}}]}

data: {"choices":[{"delta":{"content":","}}]}

data: {"choices":[{"delta":{"content":" world"}}]}

data: {"choices":[{"delta":{"content":"!"}}]}

data: [DONE]
```

The rules of this format:

- Each event is a line starting with **`data: `** followed by a JSON object, then a blank line.
- The token text is at **`choices[0].delta.content`**. (`delta` = "what's new in this chunk.")
- A final literal **`data: [DONE]`** signals the end. It is **not** JSON — don't try to parse it.
- Some chunks carry no `content` (e.g. the first/last, or role markers) — skip those.

> **SSE vs WebSocket:** SSE is a *one-way* (server→client) streaming format over plain HTTP. The LLM API uses SSE to stream to **us** (our server). We then use a **WebSocket** to stream to the **browser** (two-way, so the user can also send/cancel). Two different channels, each suited to its direction.

## Concept: consuming a stream with httpx

Regular `await client.get(...)` waits for the *whole* body. For streaming you use **`client.stream(...)`** as an `async with` block and iterate the body **as it arrives** with `aiter_lines()`:

```python
import json
import httpx


async def stream_tokens(client, url, payload, headers):
    """Yield LLM tokens one at a time from an OpenAI-compatible SSE endpoint.

    Args:
        client: an httpx.AsyncClient.
        url: the chat/completions endpoint.
        payload: request body dict (must include "stream": True).
        headers: dict with auth, e.g. {"Authorization": "Bearer <key>"}.
    Yields:
        str: each token's text, in order, as it arrives. Stops at [DONE].
    """
    async with client.stream("POST", url, json=payload, headers=headers) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():     # lines as they stream in
            if not line.startswith("data: "):          # skip blank lines & non-data lines
                continue
            data = line[len("data: "):]                # strip the "data: " prefix
            if data == "[DONE]":                        # end-of-stream sentinel (not JSON)
                break
            chunk = json.loads(data)                    # parse the JSON event
            delta = chunk["choices"][0]["delta"]        # the new bit in this chunk
            token = delta.get("content")                # may be absent on some chunks
            if token:
                yield token                             # hand this token to the caller
```

Key points, explained:

- **`client.stream("POST", ...)`** opens the connection and lets you read the body incrementally — it does *not* buffer the whole response. It must be used as `async with`.
- **`response.aiter_lines()`** is an **async generator** of text lines as they arrive over the network — exactly the `async for` pattern from Section 01.02.
- We **skip** non-`data:` lines (including the blank separators), **break** on `[DONE]`, parse the rest, and `yield` only chunks that actually carry `content`.
- Because `stream_tokens` itself `yield`s, it's an **async generator** — the caller consumes it with `async for token in stream_tokens(...)`.

```mermaid
flowchart LR
    A["client.stream POST"] --> B["aiter_lines()"]
    B --> C{line starts<br/>with 'data: '?}
    C -- no --> B
    C -- yes --> D{== '[DONE]'?}
    D -- yes --> E[stop]
    D -- no --> F["json.loads → delta.content"]
    F --> G{has content?}
    G -- yes --> H[yield token]
    G -- no --> B
    H --> B
```

## Verified: stream from a local mock that speaks the real format

We can't reach the live API here, so we run a tiny local server that emits **the exact SSE wire format** above, then consume it with the real `stream_tokens`:

```python
# stream_demo.py
import asyncio
import json
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import httpx


# --- a local server that streams SSE chunks just like the LLM API would ---
class MockSSEHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for piece in ["Hello", ",", " world", "!"]:
            event = {"choices": [{"delta": {"content": piece}}]}
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            self.wfile.flush()                 # push each chunk immediately (don't buffer)
            time.sleep(0.05)                   # pretend the model "thinks" between tokens
        self.wfile.write(b"data: [DONE]\n\n")  # end-of-stream marker
        self.wfile.flush()

    def log_message(self, *args):
        pass


threading.Thread(
    target=lambda: ThreadingHTTPServer(("127.0.0.1", 8141), MockSSEHandler).serve_forever(),
    daemon=True,
).start()
time.sleep(0.3)


# --- the real consumer (same code as above) ---
async def stream_tokens(client, url, payload, headers):
    async with client.stream("POST", url, json=payload, headers=headers) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = line[len("data: "):]
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            token = chunk["choices"][0]["delta"].get("content")
            if token:
                yield token


async def main():
    url = "http://127.0.0.1:8141/v1/chat/completions"
    payload = {"model": "mock", "messages": [{"role": "user", "content": "hi"}], "stream": True}
    headers = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("streaming: ", end="", flush=True)
        full = ""
        async for token in stream_tokens(client, url, payload, headers):
            print(token, end="", flush=True)   # appears piece by piece, like typing
            full += token
        print()
        print("assembled:", repr(full))


asyncio.run(main())
```

**Verified output:**

```
streaming: Hello, world!
assembled: 'Hello, world!'
```

Each token arrived separately (0.05s apart) and we printed it the instant it came in — the streaming "typing" effect — then assembled the full message. This `stream_tokens` generator is the heart of the AI project.

## Concept: pointing it at the real endpoints

The consumer code doesn't change — only the URL, headers, and payload do:

**NVIDIA (needs a free API key):**

```python
# illustrative — needs NVIDIA_API_KEY and internet; NOT executed in this course
import os
url = "https://integrate.api.nvidia.com/v1/chat/completions"
headers = {"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}"}
payload = {
    "model": "moonshotai/kimi-k2.6",
    "messages": [{"role": "user", "content": "Which is larger, 9.11 or 9.8?"}],
    "max_tokens": 1024,
    "temperature": 0.2,
    "stream": True,                 # <-- the switch that turns on SSE streaming
}
# async for token in stream_tokens(client, url, payload, headers): ...
```

**Ollama (local, no key):**

```python
# illustrative — needs Ollama running locally with a model pulled
url = "http://localhost:11434/v1/chat/completions"
headers = {}                         # no auth for local Ollama
payload = {
    "model": "llama3.2",            # whatever you've `ollama pull`ed
    "messages": [{"role": "user", "content": "Say hi"}],
    "stream": True,
}
```

> Both are **not executed here** (no key / no local server in the sandbox), but they use the *same verified* `stream_tokens`. The only differences are the URL, the auth header, and the model name.

> **Thinking models (aside):** some models (like Kimi) can emit *reasoning* separately in `delta.reasoning_content` before the real answer in `delta.content`. Our generator yields only `content`, so reasoning is naturally skipped. If you want to show the model's thinking, also read `delta.get("reasoning_content")`.

## Common mistakes

**Mistake: trying to `json.loads("[DONE]")`.** It's a literal sentinel, not JSON — parsing it raises `JSONDecodeError`. Check for `== "[DONE]"` and `break` before parsing.

**Mistake: using `client.get`/awaiting the whole response.** `await client.post(...)` waits for the *entire* answer, defeating streaming — you'd get all tokens at once at the end. Use `client.stream(...)` + `aiter_lines()`.

**Mistake: forgetting `"stream": True` in the payload.** Without it the server returns a single non-SSE JSON object, and `aiter_lines()` won't find `data:` events. The token loop yields nothing.

**Mistake: assuming every chunk has content.** Role/finish chunks have an empty or absent `content`. Always use `delta.get("content")` and skip falsy values, or you'll `yield` `None`/`""`.

## Practice

**Exercise:** Extend `stream_tokens` to also detect the LLM's *finish reason*. OpenAI-compatible chunks include `choices[0].finish_reason` (e.g. `"stop"`, `"length"`) on the final content chunk. Make the generator `print` the finish reason when present (still yielding tokens as before).

<details><summary>Solution</summary>

```python
async def stream_tokens(client, url, payload, headers):
    async with client.stream("POST", url, json=payload, headers=headers) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = line[len("data: "):]
            if data == "[DONE]":
                break
            choice = json.loads(data)["choices"][0]
            reason = choice.get("finish_reason")
            if reason:
                print(f"[finish_reason: {reason}]")
            token = choice["delta"].get("content")
            if token:
                yield token
```

`finish_reason` is `None` on normal token chunks and set (e.g. `"stop"`) on the last one — handy for knowing *why* the model stopped (natural end vs hit the `max_tokens` limit).
</details>

## Recap & next

- ✅ Streaming LLM responses use **SSE**: lines of `data: <json>`, token text at `choices[0].delta.content`, ending with `data: [DONE]`.
- ✅ Consume it with **`client.stream(...)`** + **`aiter_lines()`**, skipping non-data/empty lines and breaking on `[DONE]`.
- ✅ Wrap it in an **async generator** that `yield`s tokens — verified against a local mock of the real wire format.
- ✅ The same consumer works for NVIDIA and Ollama; only URL/headers/model change. Always set `"stream": True`.
- Self-check: why must you check for `[DONE]` *before* calling `json.loads`?

→ Next: **[02 · Bridge SSE → WebSocket](02_bridge_sse_to_ws.md)** — push these tokens to the browser.
