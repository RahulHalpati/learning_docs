# 01: WebSocket basics

> **Level:** Beginner → Intermediate · **Prerequisites:** [Section 02](../02_fastapi_basics/README.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-03 (FastAPI 0.136.1, websockets 16.0)

## Why this matters

HTTP can't push. The server only ever *answers* a request — it can't send you something out of the blue. A live AI reply that appears token-by-token needs the *server* to keep sending. **WebSockets** are how. This module builds the smallest possible WebSocket server, connects to it from a browser, and explains the lifecycle you'll reuse everywhere after.

## Concept: HTTP vs WebSocket

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    Note over C,S: HTTP — one round trip, then closed
    C->>S: GET /thing
    S-->>C: response
    Note over C,S: connection closed; server can't speak again

    Note over C,S: WebSocket — stays open, both can send anytime
    C->>S: HTTP request with "Upgrade: websocket"
    S-->>C: 101 Switching Protocols
    Note over C,S: connection now open both ways
    C->>S: message
    S-->>C: message
    S-->>C: message (server pushes, unprompted!)
    C->>S: message
```

| | HTTP request | WebSocket |
|---|---|---|
| Lifetime | one request → one response, then closed | stays open until either side closes |
| Direction | client asks, server answers | **both** sides send anytime |
| Server push? | ❌ no | ✅ yes |
| Good for | fetching/submitting data | live chat, notifications, **token streaming** |

A WebSocket starts life as a normal HTTP request carrying an `Upgrade: websocket` header. The server agrees with status **101 Switching Protocols** — the **handshake** — and from then on the TCP connection is a two-way message pipe. You don't code the handshake yourself; FastAPI does it when you call `await websocket.accept()`.

> **URL scheme:** WebSocket URLs use `ws://` (or `wss://` for TLS/encrypted, the WebSocket equivalent of `https://`). Example: `ws://localhost:8000/ws`.

## Concept: the WebSocket endpoint and its lifecycle

In FastAPI you declare a WebSocket endpoint with `@app.websocket(...)` instead of `@app.get(...)`. The handler receives a `WebSocket` object and follows a clear lifecycle:

```python
# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


@app.websocket("/ws")                       # note: .websocket, not .get
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()                # 1. complete the handshake — REQUIRED first
    try:
        while True:                         # 2. loop, handling messages as they arrive
            data = await websocket.receive_text()   # waits for the next client message
            await websocket.send_text(f"Echo: {data}")   # send a message back
    except WebSocketDisconnect:             # 3. client closed the connection
        print("Client disconnected")
```

The four lifecycle steps:

1. **`await websocket.accept()`** — completes the handshake. **You must call this first**; until you do, no messages flow.
2. **`await websocket.receive_text()`** — waits (yielding control, like all `await`) for the next text message from the client. There's also `receive_json()` and `receive_bytes()`.
3. **`await websocket.send_text(...)`** — push a message to the client. Also `send_json(...)`, `send_bytes(...)`.
4. **`WebSocketDisconnect`** — raised when the client disconnects. The `while True` loop would otherwise run forever; catching this is how you exit cleanly. **Always wrap the loop in `try/except WebSocketDisconnect`.**

> Everything is `async`/`await` — exactly the Section 01 skills. A WebSocket handler is just a long-lived coroutine that mostly waits on `receive_*`.

## Verified: testing the echo server

`TestClient` can drive WebSockets in-process — no running server, no `websockets` network library needed:

```python
# test_ws.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_echo():
    with client.websocket_connect("/ws") as ws:   # opens + accepts the connection
        ws.send_text("hello")
        print(ws.receive_text())
        ws.send_text("world")
        print(ws.receive_text())
    # leaving the 'with' block closes the connection (raises WebSocketDisconnect server-side)

test_echo()
```

**Verified output:**

```
Echo: hello
Echo: world
```

The server received each message and pushed a reply — a live two-way exchange over one open connection.

## A real browser client

The echo server is more fun from a browser. Save this as `index.html` and open it while `fastapi dev main.py` is running:

```html
<!-- index.html -->
<!DOCTYPE html>
<html>
<body>
  <h3>WebSocket echo</h3>
  <input id="msg" placeholder="type a message" />
  <button onclick="send()">Send</button>
  <ul id="log"></ul>

  <script>
    // open a WebSocket to our endpoint (note ws://, not http://)
    const ws = new WebSocket("ws://localhost:8000/ws");

    // fires when the server sends us a message
    ws.onmessage = (event) => {
      const li = document.createElement("li");
      li.textContent = event.data;          // event.data is the text the server sent
      document.getElementById("log").appendChild(li);
    };

    function send() {
      const input = document.getElementById("msg");
      ws.send(input.value);                  // send text to the server
      input.value = "";
    }
  </script>
</body>
</html>
```

The browser's built-in `WebSocket` object is the client side: `new WebSocket(url)` opens it, `ws.onmessage` fires whenever the server pushes, and `ws.send(...)` sends. Type a message, hit Send, and "Echo: …" appears — pushed by the server. (This page is a manual/browser check; the *server* behavior it relies on is the verified echo above.)

> **CORS note:** WebSockets aren't restricted by the browser's same-origin CORS rules the way `fetch` is, so a local HTML file can usually connect to `ws://localhost:8000` directly. In Section 99 we'll serve the HTML *from* FastAPI itself, which sidesteps the issue entirely.

## Common mistakes

**Mistake: forgetting `await websocket.accept()`.** Without it the connection never opens; clients hang or get rejected. It must be the first thing you do.

**Mistake: no `try/except WebSocketDisconnect`.**

```python
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()   # ❌ when client leaves, this raises
        await websocket.send_text(data)          #    and crashes the handler with a traceback
```
When the client closes, `receive_text()` raises `WebSocketDisconnect`. Unhandled, it logs an ugly error every time anyone disconnects. **Fix:** wrap the loop in `try/except WebSocketDisconnect`.

**Mistake: using `http://` for the client URL.** It's `ws://` (or `wss://`). `new WebSocket("http://...")` throws.

## Practice

**Exercise:** Change the echo endpoint so it replies with the message **reversed** and uppercased (e.g. send `"hello"` → receive `"OLLEH"`). Write a `TestClient` test verifying it.

<details><summary>Solution</summary>

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(data[::-1].upper())   # reverse, then uppercase
    except WebSocketDisconnect:
        pass
```
```python
def test_reverse():
    with client.websocket_connect("/ws") as ws:
        ws.send_text("hello")
        assert ws.receive_text() == "OLLEH"
```
`data[::-1]` reverses a string; `.upper()` uppercases it. (Verified: `"hello"` → `"OLLEH"`.)
</details>

## Recap & next

- ✅ WebSockets keep one connection open so the **server can push** — what HTTP can't do.
- ✅ Declare with `@app.websocket("/path")`; lifecycle is **accept → (receive/send loop) → handle disconnect**.
- ✅ Always `await websocket.accept()` first and wrap the loop in `try/except WebSocketDisconnect`.
- ✅ Browser side: `new WebSocket("ws://...")`, `ws.onmessage`, `ws.send(...)`.
- Self-check: why can't a plain HTTP endpoint stream an AI reply token-by-token, but a WebSocket can?

→ Next: **[02 · Connection manager](02_connection_manager.md)** — handle many clients at once.
