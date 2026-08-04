# 08-1 · Structured logging

> **Level:** Intermediate · **Prerequisites:** [05-3 · Middleware & CORS](../05_api_design_and_robustness/03_middleware_and_cors.md)
> **Time:** 30 min · **Verified:** 2026-07-27 (stdlib logging)

## Why this matters

`print()` debugging doesn't survive contact with production. When something breaks at 2am across many requests and workers, you need logs you can **search and correlate**: structured (JSON) lines, each tagged with a **request id** so you can follow one request end to end. That's the difference between "grep and pray" and "filter to request `abc123` and read the story."

---

## JSON logs

Format log records as one JSON object per line — a log aggregator (Loki, ELK, CloudWatch) can then index and query fields:

```python
# app/core/logging.py (essentials)
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {"level": record.levelname, "logger": record.name,
                   "message": record.getMessage()}
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        return json.dumps(payload)

def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)
```

`configure_logging()` runs once at startup (in the app's lifespan). Logs go to **stdout** — in containers, that's the right place; the platform collects them (12-factor: treat logs as an event stream, don't manage log files).

A line looks like:
```json
{"level": "INFO", "logger": "taskflow.access", "message": "GET /api/v1/projects -> 200 (4.1ms)", "request_id": "a1b2c3d4e5f6"}
```

---

## The request id — correlation

The middleware from [05-3](../05_api_design_and_robustness/03_middleware_and_cors.md) assigns each request an id, stores it on `request.state`, echoes it in the `x-request-id` response header, and logs it. Two payoffs:

- **Correlate:** filter your logs to one `request_id` and see every line that request produced — across services if you propagate the header.
- **Support:** a user reports an error; the `x-request-id` in their response points you straight to the relevant logs.

```python
logger.info(f"{request.method} {request.url.path} -> {response.status_code}",
            extra={"request_id": request_id})     # extra fields → JSON fields
```

`extra={...}` is how you attach structured fields to a log line without string-concatenating them into the message.

---

## Log levels & what to log

| Level | Use for |
|-------|---------|
| `DEBUG` | local detail (off in prod) |
| `INFO` | request completed, job ran, notable events |
| `WARNING` | recoverable oddities (retry, fallback) |
| `ERROR` | a request/job failed — include the exception |

> ⚠️ **Never log secrets or PII.** Passwords, tokens, full card numbers, personal data must never hit the logs — logs are widely readable and long-lived. Log the request id, method, path, status, and timing; redact or omit sensitive bodies/headers (e.g. `Authorization`). A secret in the logs is a leak.

---

## Recap & next

- ✅ Emit **JSON logs** to **stdout** (the platform collects them) — searchable, structured.
- ✅ Tag every line with a **request id** to correlate one request's whole story (and support tickets).
- ✅ Use `extra={...}` for structured fields; pick levels deliberately.
- ✅ **Never** log secrets or PII.
- ✅ Self-check: a user sends you the `x-request-id` from a failed response — what can you do with it?

→ Next: **[08-2 · Health checks](02_health_checks.md)**

## Exercises

1. Add an `ERROR` log (with the request id and exception) in the `AppError` handler for 5xx-class errors, so failures are always traceable.

<details>
<summary>Solution</summary>

In the exception handling path, `logger.error("unhandled", extra={"request_id": request.state.request_id}, exc_info=exc)` for unexpected errors. Now every failure leaves a searchable, correlated trail — while the client still sees only a safe message.
</details>
