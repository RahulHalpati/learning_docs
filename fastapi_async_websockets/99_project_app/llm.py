"""LLM backend: stream tokens from an OpenAI-compatible chat endpoint.

Three interchangeable backends, chosen by the LLM_BACKEND env var:

    LLM_BACKEND=mock     (default) no key, no internet — a canned streaming reply
    LLM_BACKEND=nvidia   NVIDIA's hosted API; requires NVIDIA_API_KEY
    LLM_BACKEND=ollama   local Ollama at http://localhost:11434

All three expose the same async generator, `stream_reply`, which yields the
assistant's tokens one at a time. The rest of the app never needs to know
which backend is active.
"""
import asyncio
import json
import os

import httpx

# Which backend to use. Read once at import time.
BACKEND = os.environ.get("LLM_BACKEND", "mock").lower()

# Model name; sensible default per backend, overridable via LLM_MODEL.
_DEFAULT_MODELS = {"nvidia": "moonshotai/kimi-k2.6", "ollama": "llama3.2"}
MODEL = os.environ.get("LLM_MODEL") or _DEFAULT_MODELS.get(BACKEND, "mock")


def _endpoint() -> tuple[str, dict]:
    """Return (url, headers) for the active real backend.

    Returns:
        A (url, headers) pair. `headers` carries auth for NVIDIA, empty for Ollama.
    Raises:
        KeyError: if NVIDIA is selected but NVIDIA_API_KEY is unset.
        ValueError: if called for an unknown backend.
    """
    if BACKEND == "nvidia":
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}"}
        return url, headers
    if BACKEND == "ollama":
        return "http://localhost:11434/v1/chat/completions", {}
    raise ValueError(f"No real endpoint for backend {BACKEND!r}")


async def stream_reply(client: httpx.AsyncClient, messages: list[dict]):
    """Yield the assistant's reply tokens for a conversation.

    Args:
        client: a shared httpx.AsyncClient (ignored by the mock backend).
        messages: OpenAI-style chat history, e.g.
            [{"role": "system", "content": "..."},
             {"role": "user", "content": "Hello"}]
    Yields:
        str: each token of the assistant's reply, in order.
    """
    if BACKEND == "mock":
        async for token in _mock_stream(messages):
            yield token
        return

    url, headers = _endpoint()
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
        "max_tokens": 1024,
    }
    # client.stream() reads the response body incrementally (SSE), not all at once.
    async with client.stream("POST", url, json=payload, headers=headers) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue                          # skip blank separators / comments
            data = line[len("data: "):]
            if data == "[DONE]":
                break                             # end-of-stream sentinel (not JSON)
            delta = json.loads(data)["choices"][0]["delta"]
            token = delta.get("content")          # absent on role/finish chunks
            if token:
                yield token


async def _mock_stream(messages: list[dict]):
    """A fake LLM: stream a canned reply word-by-word, so the app runs with no key."""
    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "",
    )
    reply = (
        f"You said: {last_user!r}. "
        "This is a mock streaming reply, sent one word at a time so you can see "
        "the typing effect without an API key. Set LLM_BACKEND=nvidia or "
        "LLM_BACKEND=ollama to talk to a real model."
    )
    for word in reply.split(" "):
        await asyncio.sleep(0.05)                 # pretend the model is "thinking"
        yield word + " "
