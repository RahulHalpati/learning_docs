# 09-1 · Gunicorn & WSGI

> **Level:** Intermediate · **Prerequisites:** [04-1 · The application factory](../04_app_structure/01_app_factory.md)
> **Time:** 40 min · **Verified:** 2026-07-29 (gunicorn 26.0.0 — served the real app)

## Why this matters

`flask run` prints a warning for a reason: it's a **development server**. Single-worker, not hardened, not built for concurrency. Every real Flask deployment puts a production **WSGI server** — gunicorn — in front. This is the single most common Flask production mistake, and it's a one-line fix.

---

## WSGI in one paragraph

**WSGI** is the Python standard interface between a web server and a Python app. Your Flask app is a WSGI callable; gunicorn is a WSGI server that accepts connections, manages worker processes, and calls your app for each request. That contract is why any WSGI server can run any Flask app.

---

## The entrypoint

Gunicorn needs a module-level app object to import:

```python
# wsgi.py
from app import create_app

app = create_app()          # built once, at process start
```

```bash
gunicorn -w 4 -b 0.0.0.0:8000 'wsgi:app'
```

`'wsgi:app'` = "the `app` object in `wsgi.py`". **Verified against the real app:**

**Output (real run, gunicorn with 2 workers):**
```
GET /healthz          ->  {"status": "ok"}
GET /                 ->  <title>FlaskNotes</title>          (HTML)
GET /api/v1/notes     ->  401                                (auth enforced)
GET /api/v1/nope      ->  {"error": {..., "status": 404}}    (JSON, not HTML)
```

The same app that ran under `flask run` now serves through a production server, with content negotiation intact.

---

## Workers

```bash
gunicorn -w 4 -b 0.0.0.0:8000 --access-logfile - 'wsgi:app'
```

- **`-w 4`** — worker *processes*. Each handles one request at a time (sync workers), so 4 workers = 4 concurrent requests. Rule of thumb: **`(2 × CPU cores) + 1`**.
- **`--access-logfile -`** — access logs to stdout ([07-2](../07_errors_logging_cors/02_logging.md)).
- **`--timeout 30`** — kill a worker stuck longer than this.

For I/O-heavy apps, `-k gevent` (async workers) serves far more concurrent connections per worker. Start with sync workers; change only if you measure a need.

> ⚠️ **Workers are separate processes — never keep state in module-level Python variables.** An in-memory counter, cache, or "logged-in users" dict will be different in each worker, so requests get inconsistent answers depending on which one handles them. Shared state belongs in the database or Redis.

---

## Behind a reverse proxy

Production usually runs **Nginx (or a cloud load balancer) → gunicorn → Flask**. The proxy terminates TLS, serves static files, and buffers slow clients. Flask then needs to be told to trust the proxy's headers:

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
```

Without `ProxyFix`, `request.remote_addr` is the proxy's IP (breaking rate limits and logs) and external URLs are generated as `http://` even on an HTTPS site.

> ⚠️ Only enable `ProxyFix` when you're **actually** behind a trusted proxy. If the app is directly reachable, a client can spoof `X-Forwarded-For` and defeat any IP-based logic.

---

## Recap & next

- ✅ `flask run` is **development only**; production uses **gunicorn** (a WSGI server).
- ✅ `wsgi.py` exposes `app = create_app()`; run `gunicorn -w 4 -b 0.0.0.0:8000 'wsgi:app'`.
- ✅ Workers ≈ `(2 × cores) + 1`; they're **separate processes** — no shared in-memory state.
- ✅ Behind a proxy, add **`ProxyFix`** (and only then).
- ✅ Self-check: why does an in-memory rate-limit counter misbehave with `-w 4`?

→ Next: **[09-2 · Docker & compose](02_docker_deploy.md)**

## Exercises

1. Run the capstone under gunicorn with 2 workers and hit `/healthz` and `/api/v1/notes`. Confirm the API returns 401 and the health check 200.

<details>
<summary>Solution</summary>

`gunicorn -w 2 -b 127.0.0.1:8000 'wsgi:app'`, then `curl localhost:8000/healthz` → `{"status": "ok"}` and `curl -o /dev/null -w "%{http_code}" localhost:8000/api/v1/notes` → `401`. That's the exact verification run shown above.
</details>
