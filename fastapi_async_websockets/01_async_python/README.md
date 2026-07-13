# Section 01 · Async Python

> **Prerequisites:** [00 · Introduction](../00_introduction.md) · comfortable with Python functions and classes.
> **Time:** ~3–4 hours.

Before any web code, you need to understand **async**. FastAPI and WebSockets are async to their core — if `async`/`await` is mysterious, everything later feels like magic. This section removes the magic.

## Modules

| # | Module | You'll learn |
|---|--------|--------------|
| 01 | [Why async?](01_why_async.md) | What problem async solves; I/O-bound vs CPU-bound; concurrency vs parallelism |
| 02 | [`async` / `await`](02_async_await.md) | Coroutines, the event loop, `await`, `asyncio.gather`, tasks |
| 03 | [Real async I/O with httpx](03_async_io_httpx.md) | Actually awaiting the network; why `time.sleep` and `requests` break async |

## What you'll be able to do after this section

- Read async code and predict its execution order.
- Write coroutines and run several concurrently with `asyncio.gather`.
- Explain *when* async helps (and when it doesn't).
- Make concurrent network calls with `httpx.AsyncClient`.

→ Start: **[01 · Why async?](01_why_async.md)**
