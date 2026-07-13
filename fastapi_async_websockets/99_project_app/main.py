"""Real-time streaming AI chat — FastAPI + WebSockets + async LLM streaming.

Run it:
    pip install "fastapi[standard]" httpx
    fastapi dev main.py
    # open http://127.0.0.1:8000

By default it uses a no-key mock backend (see llm.py). To use a real model:
    LLM_BACKEND=nvidia NVIDIA_API_KEY=nvapi-xxx fastapi dev main.py
    # or
    LLM_BACKEND=ollama fastapi dev main.py     # needs Ollama running locally

WebSocket protocol on /ws/chat:
    client -> server : the prompt text, or the literal "__stop__" to interrupt
    server -> client : {"type":"token","content":"..."}   one per token
                       {"type":"end","stopped":<bool>}     reply finished
                       {"type":"error","detail":"..."}     something failed
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

import llm

STOP_SIGNAL = "__stop__"
SYSTEM_PROMPT = {"role": "system", "content": "You are a concise, friendly assistant."}
INDEX_HTML = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One shared HTTP client for the app's lifetime. timeout=None so long
    # streamed replies are never cut off by a read timeout.
    app.state.client = httpx.AsyncClient(timeout=None)
    yield
    await app.state.client.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index() -> HTMLResponse:
    """Serve the chat UI (so the page and the WebSocket share an origin)."""
    return HTMLResponse(INDEX_HTML)


async def stream_one_reply(
    websocket: WebSocket, client: httpx.AsyncClient, history: list[dict]
) -> str:
    """Stream one assistant reply, interruptible by a '__stop__' message.

    Runs two tasks concurrently on the socket: one streams the LLM reply and
    forwards each token; the other listens for a stop signal. Whichever finishes
    first wins, and the other is cancelled.

    Returns:
        The assembled reply text (partial if the user stopped early).
    Raises:
        WebSocketDisconnect: if the client disconnects mid-reply (so the caller
            can exit its loop).
    """
    collected: list[str] = []

    async def do_stream() -> None:
        async for token in llm.stream_reply(client, history):
            collected.append(token)
            await websocket.send_json({"type": "token", "content": token})

    async def listen_for_stop() -> bool:
        # Only this coroutine reads from the socket while a reply streams,
        # so there is never more than one concurrent receive on the socket.
        while True:
            message = await websocket.receive_text()
            if message == STOP_SIGNAL:
                return True
            # any non-stop message during streaming is ignored

    stream_task = asyncio.create_task(do_stream())
    stop_task = asyncio.create_task(listen_for_stop())

    done, pending = await asyncio.wait(
        {stream_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()                            # stop whichever didn't finish

    # Surface a disconnect or an LLM error from whichever task completed.
    for task in done:
        exc = task.exception()
        if isinstance(exc, WebSocketDisconnect):
            raise exc                            # let the caller's loop end
        if exc is not None:
            await websocket.send_json({"type": "error", "detail": str(exc)})
            return "".join(collected)

    stopped = stop_task in done and stop_task.result() is True
    await websocket.send_json({"type": "end", "stopped": stopped})
    return "".join(collected)


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    client: httpx.AsyncClient = app.state.client
    history: list[dict] = [SYSTEM_PROMPT]        # per-connection conversation memory
    try:
        while True:
            prompt = await websocket.receive_text()
            if prompt == STOP_SIGNAL:
                continue                         # stray stop while idle: ignore
            history.append({"role": "user", "content": prompt})
            reply = await stream_one_reply(websocket, client, history)
            if reply:
                history.append({"role": "assistant", "content": reply})
    except WebSocketDisconnect:
        pass                                     # client closed the tab — done
