# 07-2 · Logging

> **Level:** Intermediate · **Prerequisites:** [07-1 · Error handling](01_error_handling.md)
> **Time:** 35 min · **Verified:** 2026-07-29 (Flask 3.1.3, stdlib logging)

## Why this matters

When something breaks in production you can't attach a debugger — logs are all you have. Flask uses Python's standard `logging`, and configuring it deliberately (once, in the factory) is the difference between "we can see what happened" and "no idea".

---

## Configure it in the factory

```python
import logging, sys

def _configure_logging(app):
    handler = logging.StreamHandler(sys.stdout)             # stdout, not a file
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if app.debug else logging.INFO)
```

Called from `create_app()` before anything else. Two choices worth understanding:

- **Log to stdout, not files.** In containers the platform collects stdout; managing log files inside a container is a mistake (rotation, disk, lost on restart). This is the 12-factor "logs are event streams" rule.
- **Level from `app.debug`** — verbose locally, INFO in production.

---

## Using it

```python
from flask import current_app
current_app.logger.info("Note created id=%s user=%s", note.id, user.id)

# or a module logger (preferred in library-ish code)
logger = logging.getLogger(__name__)
logger.warning("Upload rejected: %s", filename)
```

**Output (real run, from the 500 handler):**
```
[2026-08-05 22:30:05,704] ERROR in app: boom
Traceback (most recent call last):
  ...
ValueError: kaboom
```

`logger.exception(...)` (used in the error handler) logs at ERROR **and** attaches the traceback — always use it inside an `except` block.

> **Tip — use `%s` placeholders, not f-strings.** `logger.info("user=%s", uid)` defers formatting until the record is actually emitted, so a filtered-out DEBUG line costs nothing. It also lets log aggregators group identical messages.

---

## Levels

| Level | Use for |
|-------|---------|
| `DEBUG` | detailed local tracing (off in production) |
| `INFO` | notable events: created, logged in, job ran |
| `WARNING` | recoverable oddities: rejected upload, retry |
| `ERROR` | a request failed — include the exception |
| `CRITICAL` | the app can't function |

---

## What not to log

> ⚠️ **Never log passwords, tokens, session cookies, or personal data.** Logs are widely readable (ops, aggregators, backups) and long-lived. Log *identifiers*, not payloads: `user=42`, not the whole request body; "login failed for user 42", never the attempted password. A secret in the logs is a leak that survives long after the request.

Be careful with `logger.debug("body=%s", request.get_json())` — a handy line that quietly ships credentials into your log store.

---

## Production logging worth having

- **Request id** — generate one per request in `before_request`, attach it to every log line and return it in a header, so a user's bug report maps to exact log lines.
- **Access logs** — gunicorn produces them; add `--access-logfile -` to send them to stdout.
- **Structured (JSON) logs** — if you use an aggregator (Loki/ELK/CloudWatch), a JSON formatter makes fields queryable.
- **Don't log health checks** — they'll drown everything else.

---

## Recap & next

- ✅ Configure logging **once** in the factory; log to **stdout**; level from `app.debug`.
- ✅ `logger.exception(...)` inside `except` for traceback capture; `%s` placeholders, not f-strings.
- ✅ Pick levels deliberately (INFO events, WARNING oddities, ERROR failures).
- ✅ **Never log secrets or PII** — log ids instead.
- ✅ Self-check: why does `logger.info("user=%s", uid)` beat `logger.info(f"user={uid}")`?

→ Next: **[07-3 · CORS & middleware](03_cors_and_middleware.md)**

## Exercises

1. Add a `before_request` that assigns `g.request_id = uuid4().hex[:12]` and an `after_request` that returns it as an `X-Request-ID` header; include it in a log line.

<details>
<summary>Solution</summary>

Set it on `g` in `before_request`, read it in `after_request` to set the header, and pass it into log calls (`logger.info("... rid=%s", g.request_id)`). Now a user's `X-Request-ID` points you straight at their log lines — the cheapest debugging win in production.
</details>
