# 07-3 · CORS & middleware

> **Level:** Intermediate · **Prerequisites:** [07-1 · Error handling](01_error_handling.md)
> **Time:** 35 min · **Verified:** 2026-07-29 (Flask 3.1.3, flask-cors 6.0.5)

## Why this matters

The day a frontend developer calls your API, they hit *"blocked by CORS policy"* — even though the endpoint works fine in `curl`. Understanding CORS (and Flask's request hooks) turns that from a mystery into a two-line fix.

---

## CORS

Browsers block a page on `https://app.example.com` from calling `https://api.example.com` unless the API says it's allowed. `flask-cors` adds the headers:

```python
from flask_cors import CORS

CORS(app, resources={r"/api/*": {"origins": ["https://example.com"]}})
```

**Output (real run):**
```
request with Origin: https://example.com  ->  Access-Control-Allow-Origin: https://example.com
request with Origin: https://evil.com     ->  (no header — the browser blocks it)
```

Scoping to `r"/api/*"` is deliberate: the HTML pages are same-origin and don't need it.

Two things everyone gets wrong:

- **CORS is a *browser* rule, not security.** `curl`, mobile apps, and server-to-server calls ignore it completely. It never protects your API — it *relaxes* a browser restriction. Auth is what protects your API.
- **`origins="*"` is for local dev only.** In production, list real origins. With credentials (cookies) a wildcard is both dangerous and rejected by browsers.

> **Tip — the preflight.** For anything beyond a simple GET/POST, the browser first sends an `OPTIONS` request asking permission. `flask-cors` answers it automatically. If you see a failing `OPTIONS` in the network tab, that's the preflight — usually a missing allowed **header** (like `Authorization`) or method.

---

## Request hooks

Flask lets you run code around every request:

```python
@app.before_request
def before():
    g.start = time.perf_counter()          # runs before EVERY view

@app.after_request
def after(response):
    response.headers["X-Response-Time"] = f"{time.perf_counter() - g.start:.3f}s"
    return response                        # MUST return the response

@app.teardown_request
def teardown(exc):
    ...                                    # runs even if the view raised
```

| Hook | Runs | Typical use |
|------|------|-------------|
| `before_request` | before the view | request id, timing, auth checks |
| `after_request` | after a **successful** response | headers, CORS, timing |
| `teardown_request` | always, even on exception | cleanup, closing resources |

Scope them to a blueprint with `@bp.before_request` ([04-2](../04_app_structure/02_blueprints.md)) to guard one section.

> ⚠️ **`after_request` doesn't run if the view raised** an unhandled exception — use `teardown_request` for cleanup that must always happen.

---

## Security headers

A tiny `after_request` adds meaningful hardening:

```python
@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"              # clickjacking
    response.headers["Referrer-Policy"] = "same-origin"
    return response
```

(Add `Strict-Transport-Security` when you're on HTTPS, and a `Content-Security-Policy` when you can — CSP is the strongest XSS defense after autoescaping.)

---

## WSGI middleware

Below Flask, WSGI middleware wraps the whole app. The one you'll actually need in production is `ProxyFix`, so Flask sees the real client IP and scheme behind a reverse proxy:

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
```

Without it, `request.remote_addr` is your load balancer and `url_for(..., _external=True)` generates `http://` URLs behind an HTTPS proxy ([09-1](../09_production/01_gunicorn_wsgi.md)).

---

## Recap & next

- ✅ `CORS(app, resources={r"/api/*": {"origins": [...]}})` — scope it, list real origins, never `*` in production.
- ✅ CORS is a **browser** rule and **not** security; auth protects the API.
- ✅ Hooks: `before_request` / `after_request` (must return the response) / `teardown_request` (always runs).
- ✅ Add security headers in `after_request`; add **`ProxyFix`** when behind a proxy.
- ✅ Self-check: your API works in `curl` but the browser reports CORS. Who is blocking it, and does that mean your API is insecure?

→ Next: **[08 · Testing](../08_testing/README.md)**

## Exercises

1. Add a `before_request`/`after_request` pair that logs `METHOD path -> status (Xms)` for every request.

<details>
<summary>Solution</summary>

Store `g.start = time.perf_counter()` in `before_request`; in `after_request` compute the elapsed time and `current_app.logger.info("%s %s -> %s (%.1fms)", request.method, request.path, response.status_code, elapsed*1000)`, then **return response**. Forgetting that return is the classic `after_request` bug — Flask then has no response to send.
</details>
