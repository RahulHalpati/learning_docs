# Section 03 · WebSockets

> **Prerequisites:** [Section 02 · FastAPI basics](../02_fastapi_basics/README.md).
> **Time:** ~3–4 hours.

Regular HTTP is "ask once, get one answer, hang up." That can't power a live chat where the server pushes tokens to you as they're generated. **WebSockets** keep a single connection open so both sides can send messages anytime. This section takes you from a one-line echo server to managing many clients and running send/receive concurrently — the exact skill the streaming AI chat needs.

## Modules

| # | Module | You'll learn |
|---|--------|--------------|
| 01 | [WebSocket basics](01_websocket_basics.md) | HTTP vs WS, the handshake, the accept→receive→send→close lifecycle, a browser client |
| 02 | [Connection manager](02_connection_manager.md) | Track many clients, broadcast, handle disconnects cleanly |
| 03 | [Concurrent send & receive](03_concurrency_in_ws.md) | Push messages *and* listen at the same time with tasks — the streaming pattern |

## What you'll be able to do after this section

- Write a FastAPI WebSocket endpoint and connect to it from the browser.
- Manage multiple simultaneous connections and broadcast to all of them.
- Handle disconnects without crashing.
- Run sending and receiving concurrently — the foundation for streaming the LLM's tokens while the user can still type.

→ Start: **[01 · WebSocket basics](01_websocket_basics.md)**
