# Section 10 · Robustness & observability

> **Prerequisites:** [09 · Testing like you mean it](../09_testing/README.md) · **Time:** ~5 h

When production breaks at 3am, you have exactly two artifacts: the error body your client received and the log lines your service wrote. This section makes both worth having — **exception handlers** that turn every domain failure into one RFC 9457 problem-details shape, **middleware** that stamps each request with an ID and a timing line, **structlog** for JSON logs a machine can search and a human can read, and an **OpenAPI** schema polished enough to generate client SDKs from.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 10-1 | [Errors & exception handlers](01_errors_and_exception_handlers.md) | How do I turn every failure into one consistent, standard error shape? |
| 10-2 | [Middleware & logging](02_middleware_logging.md) | How do I trace one request through every log line it produced? |
| 10-3 | [OpenAPI, pagination & CORS](03_openapi_pagination_cors.md) | How do I make the API predictable to consume and pleasant to integrate against? |

## Mini-project

Harden **linkbox**. It works and it's tested — now make it debuggable and consumable. Three fronts:

**(a) Errors.** A domain exception hierarchy — `AppError` base carrying `code` and `status`, with `NotFoundError`, `ConflictError`, `ForbiddenError` subclasses — raised by services, mapped to HTTP in exactly one exception handler that renders RFC 9457 problem details. Validation failures get reshaped into the same format.

**(b) Middleware & logging.** A request-ID middleware and a timing middleware (pure ASGI), with structlog carrying the request ID onto every log line via contextvars.

**(c) OpenAPI polish.** Turn the auto-generated docs into something you'd hand to a paying client.

**Requirements checklist:**

- [ ] `AppError` base (`code`, `status`) with `NotFoundError`, `ConflictError`, `ForbiddenError` — raised by services; no `HTTPException` outside the API layer.
- [ ] One `@app.exception_handler(AppError)` rendering RFC 9457 problem details (`type`, `title`, `status`, `detail`, `instance` + `code` extension) with `Content-Type: application/problem+json`.
- [ ] `RequestValidationError` reshaped into the **same** problem format, with an `errors` extension carrying FastAPI's `loc`/`msg`/`type` entries.
- [ ] A last-resort 500 handler: logs the full traceback, returns a generic problem body that leaks nothing.
- [ ] Request-ID middleware: accepts an inbound `X-Request-ID` or generates a `uuid4`, binds it via `structlog.contextvars`, returns it as a response header.
- [ ] Timing middleware: one JSON log line per request with `method`, `path`, `status`, `duration_ms` — uvicorn's access log disabled in its favour.
- [ ] structlog configured with a **JSON renderer in prod, console renderer in dev** (settings-driven); uvicorn's loggers routed through the same pipeline.
- [ ] OpenAPI: `openapi_tags` with descriptions; per-endpoint `summary` and examples; documented error responses (`responses={404: {...}}` with the problem schema); `version` + `description` on the app; internal endpoints hidden with `include_in_schema=False`.

## Test task (gate)

**The 3am contract.** Complete this before starting Section 11. The requirement you're proving:

1. **Every** log line emitted during a request carries `request_id` — including lines logged from services, and including the context you carry into Arq: pass `request_id` in the job payload when you enqueue, and bind it in the worker so job log lines correlate with the request that spawned them. Authenticated requests must **also** carry `user_id` on every line.
2. The error response for **every** failure path — 404, 403, 409, 422, and 500 — is valid problem+json: `Content-Type: application/problem+json` and the fields `type`, `title`, `status`, `detail`, `instance`, with `status` matching the HTTP status code.

**Passing =** a pytest suite where:

- (a) One test captures log output for a request that logs from both the endpoint and a service (use `capsys` against the JSON renderer, or `structlog.testing.capture_logs`) and asserts `request_id` is present on **every** captured line — and `user_id` too when the request is authenticated.
- (b) One **parametrized** test drives all five failure paths (404, 403, 409, 422, 500) and asserts the content type and the five required problem fields on each.
- (c) The 500 case is triggered by a genuinely unhandled exception (plant a route that raises `RuntimeError`), and its body contains **no** stack trace, exception class name, file path, or any other internal detail — just the generic problem.

All three green, and you've earned Section 11.

## What you'll be able to do after this section

- Design a domain exception hierarchy and map it to RFC 9457 problem details in one handler — no `HTTPException` scattered through business logic.
- Explain the ASGI middleware onion, and choose between pure-ASGI and `BaseHTTPMiddleware` knowing the real trade-offs.
- Configure structlog so every log line in a request — across services and `await` points — carries `request_id` and `user_id` without passing loggers around.
- Emit one structured timing line per request and route uvicorn's own logs through the same pipeline.
- Ship an OpenAPI schema with documented tags, examples, auth, and error shapes — good enough to generate client SDKs from.

→ Start: **[10-1 · Errors & exception handlers](01_errors_and_exception_handlers.md)**
