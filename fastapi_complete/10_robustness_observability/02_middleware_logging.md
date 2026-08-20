# 10-2 · Middleware & logging

> **Level:** Intermediate→Advanced · **Prerequisites:** [10-1 · Errors & exception handlers](01_errors_and_exception_handlers.md)
> **Time:** ~50 min · **Verified:** 2026-08-07 (FastAPI 0.116 · structlog)

## Why this matters

A user reports "it failed around 2:40." Without request IDs, that's you grepping timestamps across thousands of interleaved lines from concurrent requests, guessing which `IntegrityError` belongs to which call. With request IDs it's one grep: every line the request produced — endpoint, service, DB layer, even the background job it enqueued — carries the same `request_id`, and the client has it too (it came back in a response header). This lesson builds that pipeline: middleware to stamp the request, contextvars to carry the ID, structlog to render it onto every line.

---

## The ASGI onion

Middleware wraps your app in layers. A request passes **inward** through each layer in order; the response passes back **outward** in reverse. Each layer sees the request before the app and the response after it — which is exactly the shape you need for "stamp an ID on the way in, add a header on the way out."

```
request →  [RequestId]  →  [Timing]  →  [CORS]  →  router/endpoint
response ← [RequestId]  ←  [Timing]  ←  [CORS]  ←  router/endpoint
```

One registration gotcha: `app.add_middleware(...)` **prepends** — the *last* one added is the *outermost* layer. So to get the onion above:

```python
app.add_middleware(TimingMiddleware)      # added first  → inner
app.add_middleware(RequestIdMiddleware)   # added last   → outermost, runs first
```

Order matters here for a concrete reason: the request ID must be bound *before* the timing middleware logs, or the timing line won't carry it.

---

## Same middleware, two ways

FastAPI (via Starlette) gives you two ways to write middleware. Here's a request-ID middleware in each, so you can compare honestly.

**Way 1 — `BaseHTTPMiddleware`** (the convenient one). You get `Request`/`Response` objects and a `call_next` function; it reads like a decorator:

```python
# The convenient way — fine for most apps, know its costs.
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

Its real costs — worth naming, not cargo-culting:

- **A task per request.** `call_next` runs the downstream app in a separate anyio task and re-streams the response body through an in-memory channel. That's measurable overhead on every request, forever, on your hottest path.
- **The task boundary bites edge cases.** Contextvars set *inside* the app don't propagate back out to code after `call_next`; some streaming-response and client-disconnect scenarios have historically misbehaved or deadlocked across this boundary; background-task timing can shift.
- It materializes `Request`/`Response` wrappers whether you need them or not.

**Way 2 — pure ASGI** (the production-grade one). An ASGI middleware is just a callable taking `(scope, receive, send)` — the raw protocol. No extra task, no re-streaming, no surprises:

```python
# app/middleware.py — the production-grade way
import uuid

import structlog
from starlette.datastructures import Headers, MutableHeaders


class RequestIdMiddleware:
    def __init__(self, app):
        self.app = app                                # the next layer inward

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":                   # lifespan/websocket: not ours
            return await self.app(scope, receive, send)

        # Accept the caller's ID (so traces span services) or mint one.
        request_id = Headers(scope=scope).get("x-request-id") or str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()     # never inherit a stale context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                # Echo the ID back so the client can quote it in bug reports.
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        await self.app(scope, receive, send_with_id)
```

The trade-off in one sentence: `BaseHTTPMiddleware` is easier to read and fine for low-traffic or prototype middleware; **pure ASGI is what you ship for always-on, hot-path concerns** like request IDs and timing — it's ten more lines once, and zero overhead per request forever.

---

## Why contextvars (and not thread-locals, and not passing loggers)

The naive way to get `request_id` onto every log line is to pass a logger (or the ID) into every function — noisy, and it dies the first time a third-party library logs. The old way is thread-local storage — which is **wrong under async**: one thread runs *many* interleaved requests, so a thread-local `request_id` set by request A is happily read by request B after the next `await`.

`contextvars` (stdlib) fix exactly this: each asyncio task gets its own context, and values survive across `await` points within the request but never bleed between concurrent requests. `structlog.contextvars.bind_contextvars(request_id=...)` stores the ID in that context; the `merge_contextvars` processor (below) stamps it onto **every** event dict — from your endpoint, your services, anywhere — without a single function signature changing.

One more binding belongs here: once auth resolves, bind the user too. This goes in the auth **dependency**, not the middleware, because middleware runs before the token is decoded:

```python
# in your get_current_user dependency, after decoding the token
structlog.contextvars.bind_contextvars(user_id=user.id)
```

Now every subsequent line in the request carries both IDs — that's the section gate's "3am contract."

---

## Configuring structlog

One configuration function, called once per process, settings-driven: **JSON in prod** (machines parse it — your log aggregator indexes `request_id` as a field), **console in dev** (humans read it — colored, aligned).

```python
# app/core/logging.py
import logging

import structlog

from app.core.config import settings


def configure_logging() -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,          # ← request_id/user_id land here
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    renderer = (
        structlog.dev.ConsoleRenderer()                    # dev: pretty, colored
        if settings.debug
        else structlog.processors.JSONRenderer()           # prod: one JSON object per line
    )

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy, any library) through the SAME chain,
    # so every line in the process has one format and carries the contextvars.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,               # applied to non-structlog records
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # uvicorn attaches its own handlers — strip them (no duplicate lines) and let
    # its records propagate to our root handler instead.
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True

    # We emit our own timing line (below); the stock access log is redundant noise.
    logging.getLogger("uvicorn.access").disabled = True
```

Call it before anything can log — and in *every* process that logs, which includes the Arq worker:

```python
# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import configure_logging
from app.middleware import RequestIdMiddleware, TimingMiddleware

configure_logging()                       # first — before the app object exists
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup")
    yield
    log.info("shutdown")


app = FastAPI(lifespan=lifespan)
app.add_middleware(TimingMiddleware)      # inner
app.add_middleware(RequestIdMiddleware)   # outermost — binds the ID first
```

---

## Your own access log: the timing middleware

We just disabled `uvicorn.access` — deliberately. Its line is plain text, has no `request_id`, and no duration in a parseable field. Replace it with one structured line per request that has everything you grep for at 3am:

```python
# app/middleware.py (continued)
import time

log = structlog.get_logger("linkbox.access")


class TimingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start = time.perf_counter()
        status = 500                                  # if the app dies before responding

        async def send_capture(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_capture)
        finally:                                      # log even when the app raises
            log.info(
                "request",
                method=scope["method"],
                path=scope["path"],
                status=status,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )
```

In prod that renders as one JSON line — with `request_id` merged in automatically, because `RequestIdMiddleware` (outermost) bound it before this layer logged:

```json
{"event": "request", "method": "GET", "path": "/links/abc123", "status": 200,
 "duration_ms": 12.41, "request_id": "6f1c...", "level": "info",
 "timestamp": "2026-08-07T14:02:11.512Z", "logger": "linkbox.access"}
```

---

## What to log at which level — and what never to log

- **`debug`** — developer noise: cache hits, chosen branches. Off in prod (the root level is `INFO`).
- **`info`** — one line per meaningful event: the access line, `link_created`, `job_enqueued`. Key-value pairs, not prose: `log.info("link_created", slug=slug)` beats `log.info(f"created {slug}")` — the former is queryable in your aggregator, the latter is a string.
- **`warning`** — degraded but handled: retry succeeded, fallback used, deprecated endpoint hit.
- **`error` / `log.exception`** — a request failed and a human should eventually look; `exception` adds the traceback (your 500 handler from 10-1 uses it).

**Never log:** passwords, tokens, `Authorization`/`Cookie` headers, full request bodies (they contain all of the above), or PII you don't need. A log aggregator is a database with worse access control — a token in a log line is a token leaked. If you must log a request body for debugging, allowlist fields; never dump.

---

## Recap & next

- ✅ Middleware is an **onion**: request inward in order, response outward in reverse; `add_middleware` prepends, so last-added runs first.
- ✅ `BaseHTTPMiddleware` is convenient but costs a **task per request** and misbehaves in some streaming/context cases; **pure ASGI** is the production-grade choice for hot paths.
- ✅ Request-ID middleware: **accept or generate**, bind via `structlog.contextvars`, echo in the response header; bind `user_id` in the auth dependency.
- ✅ **contextvars** are per-task, so they survive `await` and never bleed between concurrent requests — thread-locals do.
- ✅ One structlog config: **JSON renderer in prod, console in dev**; stdlib + uvicorn wired through the same chain; `uvicorn.access` replaced by your own timing line.
- ✅ Self-check: if `TimingMiddleware` were registered *after* (outside) `RequestIdMiddleware`, what exactly would be missing from the timing line, and why?

→ Next: **[10-3 · OpenAPI, pagination & CORS](03_openapi_pagination_cors.md)**

## Exercises

1. Hit your app twice with `curl -i` — once with `-H "X-Request-ID: test-123"` and once without — and verify the header behavior. Then explain: why *accept* an inbound ID at all instead of always generating one?

<details>
<summary>Solution</summary>

With the header, the response echoes `X-Request-ID: test-123` and every log line carries `request_id=test-123`; without it, both show a fresh uuid4. Accepting the inbound ID is what makes tracing work **across services**: when service A calls service B and forwards its own request ID, one grep for that ID reconstructs the whole call chain — gateway, A, B — in one view. Generate-only would give each hop a disconnected ID. (In untrusted-edge setups, validate/cap the inbound value so a client can't inject log garbage.)
</details>

2. Write a test using `structlog.testing.capture_logs()` proving that two *concurrent* requests never see each other's `request_id`. Hint: an endpoint that logs, `await`s `asyncio.sleep(0.05)`, then logs again — fire both requests with `asyncio.gather`.

<details>
<summary>Solution</summary>

```python
import asyncio


async def test_request_ids_do_not_bleed(client):
    with structlog.testing.capture_logs() as logs:
        await asyncio.gather(
            client.get("/slow-echo", headers={"X-Request-ID": "req-A"}),
            client.get("/slow-echo", headers={"X-Request-ID": "req-B"}),
        )
    a_lines = [l for l in logs if l.get("request_id") == "req-A"]
    b_lines = [l for l in logs if l.get("request_id") == "req-B"]
    assert len(a_lines) == 2 and len(b_lines) == 2   # both lines of each request kept their ID
```

The `sleep` forces the event loop to interleave the two requests on one thread. Because each request's task has its own contextvars context, the second log line of request A still says `req-A` even though request B ran in between — the exact scenario where a thread-local would have been overwritten to `req-B`.
</details>

3. Your enqueue code passes `request_id` into the Arq job payload. Write the three lines the worker function needs so its log lines correlate with the originating request.

<details>
<summary>Solution</summary>

```python
async def send_click_report(ctx, link_id: int, request_id: str):
    structlog.contextvars.clear_contextvars()                # drop the previous job's context
    structlog.contextvars.bind_contextvars(request_id=request_id)
    log.info("job_started", link_id=link_id)
    ...
```

(And `configure_logging()` in the worker's `on_startup` — the worker is a separate process; the API's logging config doesn't exist there.) `clear_contextvars` first matters because Arq reuses worker tasks: without it, a job that forgets to bind would silently log under the *previous* job's request ID — worse than no ID at all.
</details>
