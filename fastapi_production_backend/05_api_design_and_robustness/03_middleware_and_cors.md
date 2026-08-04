# 05-3 · Middleware & CORS

> **Level:** Intermediate · **Prerequisites:** [01-3 · The app factory](../01_foundations_and_structure/03_app_factory.md)
> **Time:** 30 min · **Verified:** 2026-07-27 (fastapi 0.140.8)

## Why this matters

Some behavior applies to **every** request — a request id for tracing, timing, security headers — and doesn't belong in individual routes. **Middleware** wraps every request/response to add it in one place. And **CORS** is the specific middleware that decides which browser origins may call your API — get it wrong and either your frontend is blocked or your API is dangerously open.

---

## Middleware: wrap every request

Middleware runs before and after each request. Our `RequestContextMiddleware` attaches a request id and logs one access line:

```python
# app/observability/middleware.py (essentials)
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id           # available to handlers/logs
        start = time.perf_counter()

        response = await call_next(request)              # ← the request runs here

        response.headers["x-request-id"] = request_id    # echo it back for tracing
        logger.info(f"{request.method} {request.url.path} -> {response.status_code}",
                    extra={"request_id": request_id})
        return response
```

Every response now carries an `x-request-id`, and every request produces one structured log line — with **zero** changes to any route. That request id is how you trace one request across logs (and services). This is the ideal middleware use: cross-cutting, uniform, invisible to handlers.

---

## Middleware order matters

Middleware added later wraps *outermost* and runs *first*. Add request-context and metrics **early** so they see every request, including ones that error inside inner middleware:

```python
app.add_middleware(CORSMiddleware, ...)          # added first → innermost
app.add_middleware(RequestContextMiddleware)     # added later → outer, sees everything
```

Think of it as an onion: the last-added layer is the outer skin the request hits first and the response leaves last.

---

## CORS: which browsers may call you

Browsers enforce the **same-origin policy**: JavaScript on `https://app.example.com` can't call `https://api.example.com` unless the API says it's allowed, via **CORS** headers. (Non-browser clients — mobile apps, `curl`, server-to-server — ignore CORS entirely.)

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,     # e.g. ["https://app.example.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

The critical field is **`allow_origins`** — the exact list of frontend origins permitted to call the API.

> ⚠️ **`allow_origins=["*"]` is for local dev only.** In production, list your real frontend origins explicitly. A wildcard with `allow_credentials=True` is especially dangerous (and browsers reject that combination) — it would let *any* site make credentialed requests to your API. Pull the list from settings so it differs per environment: permissive locally, locked-down in production.

---

## Other middleware you'll add

| Middleware | Purpose |
|------------|---------|
| Request id / access log | tracing (built here) |
| Metrics | Prometheus counters/latency ([08-3](../08_observability_and_ops/03_metrics_and_tracing.md)) |
| GZip | compress large responses (`GZipMiddleware`) |
| Trusted host / HTTPS redirect | security hardening |
| Rate limiting | can be middleware or a dependency ([07-2](../07_integrations/02_rate_limiting.md)) |

Add cross-cutting concerns as middleware; keep per-route logic in dependencies.

---

## Recap & next

- ✅ Middleware wraps **every** request — ideal for request ids, timing, headers; routes stay clean.
- ✅ Order is an onion: last-added is outermost and runs first — put tracing/metrics early.
- ✅ **CORS** controls which *browser* origins may call the API; list real origins in prod, never `*` with credentials.
- ✅ Pull `allow_origins` from settings so it's permissive locally, strict in production.
- ✅ Self-check: does CORS protect your API from a `curl` script or a mobile app? Why or why not?

→ Next: **[06 · Testing](../06_testing/README.md)**

## Exercises

1. Add `GZipMiddleware` (from `fastapi.middleware.gzip`) with a minimum size, and confirm a large list response comes back gzip-encoded.

<details>
<summary>Solution</summary>

`app.add_middleware(GZipMiddleware, minimum_size=1000)`. Request a large paginated list with `Accept-Encoding: gzip`; the response gains `Content-Encoding: gzip`. One line, every large response compressed — the middleware pattern paying off again.
</details>
