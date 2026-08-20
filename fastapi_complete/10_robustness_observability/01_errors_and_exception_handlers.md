# 10-1 · Errors & exception handlers

> **Level:** Intermediate→Advanced · **Prerequisites:** [09 · Testing like you mean it](../09_testing/README.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (FastAPI 0.116 · structlog)

## Why this matters

At 3am, the client team's on-call is staring at an error body and yours is staring at logs — the error shape is the only thing you two share. If your API returns `{"detail": "..."}` here, `{"error": {"message": ...}}` there, and an HTML traceback on 500s, every client grows special-casing code for each shape, and half the special cases are wrong. One standard error format, produced in one place, is not polish — it's the part of the API contract that matters most, because it's the part clients read when things are already going wrong.

---

## Error shape is an API contract

Clients *parse* your errors. A frontend decides whether to show "not found" or "try again later" by reading the body; a partner's integration retries on some errors and alerts on others. That only works if every failure — from your code, from validation, from an unhandled bug — has the **same shape**. The moment shapes diverge, error handling on the client becomes a museum of `if "detail" in body else if "message" in body` guesswork.

There is a standard for this shape: **RFC 9457 Problem Details** (the 2023 revision of RFC 7807). It's what you should return instead of ad-hoc `{"detail": ...}`:

```json
{
  "type": "https://api.linkbox.dev/problems/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "link 'abc123' does not exist",
  "instance": "/links/abc123",
  "code": "not_found"
}
```

- **`type`** — a URI identifying the *kind* of problem. Clients dispatch on it (it's stable); it can double as a docs link.
- **`title`** — short human-readable summary of the kind (same for every occurrence).
- **`status`** — the HTTP status, repeated in the body so the error is self-describing once it's in a log or a queue.
- **`detail`** — human-readable explanation of *this* occurrence.
- **`instance`** — a URI for this occurrence; the request path is the pragmatic choice.
- Anything else (`code` above, `errors` later) is an **extension member** — RFC 9457 explicitly allows them, and clients that don't know them ignore them.

And crucially: the content type is **`application/problem+json`**, not plain `application/json`. Clients and middleboxes sniff that header to know "this body is a problem document, parse it as one."

---

## The domain exception hierarchy

Recall the Section 06 rule: **services never import `HTTPException`** — HTTP is the API layer's dialect, and a service that speaks it can't be reused from a CLI, a test, or an Arq worker. Instead, services raise *domain* exceptions that say what went wrong in business terms:

```python
# app/core/exceptions.py — zero FastAPI imports; this is pure domain
class AppError(Exception):
    """Base for every failure the domain can raise.
    Services raise these; the API layer maps them to HTTP exactly once."""

    code = "app_error"    # machine-readable, STABLE across releases — clients key on it
    status = 500          # the HTTP status the API layer will use

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    code = "not_found"
    status = 404


class ConflictError(AppError):
    code = "conflict"
    status = 409


class ForbiddenError(AppError):
    code = "forbidden"
    status = 403
```

Each subclass carries its own `code` and `status` as class attributes — so *raising* an error and *mapping* it to HTTP are decided in one place each. A service now reads like the business rule it implements:

```python
# app/services/links.py — no FastAPI imports here
async def get_link(db: AsyncSession, slug: str) -> Link:
    link = await db.scalar(select(Link).where(Link.slug == slug))
    if link is None:
        raise NotFoundError(f"link '{slug}' does not exist")
    return link


async def create_link(db: AsyncSession, slug: str, url: str, owner: User) -> Link:
    if await db.scalar(select(Link).where(Link.slug == slug)):
        raise ConflictError(f"slug '{slug}' is already taken")
    ...
```

---

## One handler = one mapping point

Because every domain error inherits from `AppError`, **one** exception handler translates all of them — current and future — into problem details. First, a small helper that builds the response:

```python
# app/api/problems.py
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

PROBLEM_TYPE_BASE = "https://api.linkbox.dev/problems"


def problem_response(
    request: Request, *, status: int, detail: str, code: str, **extensions
) -> JSONResponse:
    body = {
        "type": f"{PROBLEM_TYPE_BASE}/{code}",
        "title": HTTPStatus(status).phrase,   # "Not Found", "Conflict", ... from stdlib
        "status": status,
        "detail": detail,
        "instance": str(request.url.path),
        "code": code,
        **extensions,                          # RFC 9457 extension members
    }
    # The media type IS part of the standard — not plain application/json.
    return JSONResponse(body, status_code=status, media_type="application/problem+json")
```

Then the handler — note it's registered for the **base class**, so `NotFoundError`, `ConflictError`, `ForbiddenError`, and any subclass you add next month are all covered without touching this code again:

```python
# app/main.py
from app.core.exceptions import AppError

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return problem_response(request, status=exc.status, detail=exc.detail, code=exc.code)
```

That's the whole errors architecture: services raise meaning, one handler renders shape. Adding a new failure mode is now a three-line subclass, not a new handler.

A 409 from `create_link` renders as:

```json
{
  "type": "https://api.linkbox.dev/problems/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "slug 'abc123' is already taken",
  "instance": "/links",
  "code": "conflict"
}
```

---

## Reshaping validation errors

FastAPI already returns 422s for bad input — but in its own `{"detail": [...]}` shape, which would be the one inconsistent error in your API. Override the `RequestValidationError` handler to emit the same problem format, carrying FastAPI's per-field entries as an `errors` extension:

```python
# app/main.py
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return problem_response(
        request,
        status=422,
        detail="Request validation failed.",
        code="validation_error",
        # Extension member: one entry per invalid field, in FastAPI's own terms.
        errors=[
            {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ],
    )
```

We deliberately copy **only** `loc`/`msg`/`type` from each entry. Pydantic v2's raw errors also include `input` (the submitted value) and `ctx` (which may not be JSON-serializable) — echoing `input` back means a failed login request could reflect the password into the error body and thence into client-side logs. Pick your fields; don't forward blobs.

```json
{
  "type": "https://api.linkbox.dev/problems/validation_error",
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Request validation failed.",
  "instance": "/links",
  "code": "validation_error",
  "errors": [
    {"loc": ["body", "url"], "msg": "Input should be a valid URL", "type": "url_parsing"}
  ]
}
```

---

## The last-resort 500 handler

Everything so far handles failures you *anticipated*. Bugs are the other kind — and an unhandled exception must never reach a client as a stack trace. Tracebacks leak file paths, library versions, table names, sometimes literal SQL or secrets. The rule: **the traceback goes to the logs, a generic problem goes to the client.**

```python
# app/main.py
import structlog

from app.core.config import settings

log = structlog.get_logger()

@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Full traceback → logs (with request_id bound — see 10-2). NEVER → client.
    log.exception("unhandled_error", path=request.url.path)
    detail = (
        f"{type(exc).__name__}: {exc}"   # debug convenience only —
        if settings.debug                 # in prod the branch below always wins
        else "An unexpected error occurred."
    )
    return problem_response(request, status=500, detail=detail, code="internal_error")
```

Two subtleties worth knowing:

- **Don't swallow bugs in development.** With `settings.debug` we include the exception summary in `detail` so you're not blind while iterating (an alternative is to re-raise in debug and let the console traceback speak). In production `debug` is `False`, so the body is always generic. Same shape either way — clients never see a sixth format.
- **Starlette re-raises after responding.** The `Exception` handler is special: Starlette sends your response to the client, then re-raises so the server can log it. In tests this means the test client will raise unless you pass `raise_server_exceptions=False` (`TestClient`) or `raise_app_exceptions=False` (`httpx.ASGITransport`) — exactly what the section gate's 500 test needs.

> **Tip — `HTTPException` still exists.** Framework-level 401s (e.g. from your OAuth2 dependency) still raise `HTTPException`. If you want those in problem format too, add a third handler for `StarletteHTTPException` that calls `problem_response` — same five lines, same helper.

---

## Recap & next

- ✅ Error shape is an **API contract**: clients parse it, so every failure path must produce the same shape.
- ✅ That shape is **RFC 9457 problem details** — `type`, `title`, `status`, `detail`, `instance` + extensions, served as `application/problem+json`.
- ✅ Services raise **domain exceptions** (`AppError` subclasses with `code`/`status`); no `HTTPException` outside the API layer.
- ✅ **One handler on the base class** maps the whole hierarchy; new failure modes are three-line subclasses.
- ✅ `RequestValidationError` is reshaped into the same format with an `errors` extension; the 500 handler logs the traceback and **never leaks internals**.
- ✅ Self-check: why does the handler live on `AppError` rather than one handler per subclass — what specifically would you have to do when adding `GoneError` in each design?

→ Next: **[10-2 · Middleware & logging](02_middleware_logging.md)**

## Exercises

1. Add a `RateLimitedError` (HTTP 429, code `rate_limited`) that also carries a `retry_after` seconds value, and make it appear as an extension member in the problem body — without modifying the handler.

<details>
<summary>Solution</summary>

Give the base class an extensions hook and let subclasses fill it:

```python
class AppError(Exception):
    code = "app_error"
    status = 500

    def __init__(self, detail: str, **extensions):
        self.detail = detail
        self.extensions = extensions
        super().__init__(detail)


class RateLimitedError(AppError):
    code = "rate_limited"
    status = 429

    def __init__(self, detail: str, retry_after: int):
        super().__init__(detail, retry_after=retry_after)
```

And in the (single) handler: `return problem_response(request, status=exc.status, detail=exc.detail, code=exc.code, **exc.extensions)`. Raising `RateLimitedError("slow down", retry_after=30)` now yields a problem body with `"retry_after": 30` — the handler never changed. That's the payoff of mapping on the base class.
</details>

2. Write a pytest that requests a missing link and asserts three things: status 404, `Content-Type: application/problem+json`, and that the body contains all five RFC 9457 fields with `status == 404`. Why assert the content type at all?

<details>
<summary>Solution</summary>

```python
async def test_missing_link_is_problem_json(client):
    resp = await client.get("/links/nope")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert {"type", "title", "status", "detail", "instance"} <= body.keys()
    assert body["status"] == 404
```

The content type is the machine-readable signal that "this body is a problem document" — clients (and generic HTTP tooling) dispatch their error parsing on it. If a refactor silently switches the response back to plain `application/json`, the body might look identical but standards-aware clients stop treating it as a problem document; only this assertion catches that regression.
</details>

3. A teammate proposes returning the raw exception message for 500s "because it makes support tickets easier." Name two concrete leaks this causes, using a `sqlalchemy.exc.IntegrityError` as the example.

<details>
<summary>Solution</summary>

An `IntegrityError` message typically contains (1) **schema internals** — the exact table, column, and constraint names (`duplicate key value violates unique constraint "links_slug_key"`), which map your private schema for an attacker probing for injection targets; and (2) **submitted data** — the offending values are echoed in the DETAIL line (`Key (slug)=(abc123) already exists`), which for other constraint types can include emails, tokens, or anything else the user posted. Support gets what it needs from the *logs*, correlated via `request_id` (10-2) — the client body stays generic.
</details>
