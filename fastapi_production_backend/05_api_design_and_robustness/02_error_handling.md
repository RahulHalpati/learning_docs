# 05-2 · Error handling

> **Level:** Intermediate · **Prerequisites:** [03-2 · Repository & service pattern](../03_schemas_and_crud/02_repository_service_pattern.md)
> **Time:** 30 min · **Verified:** 2026-07-27 (fastapi 0.140.8; from the TaskFlow test suite)

## Why this matters

How your API behaves when things go *wrong* is a hallmark of quality. Consumers need **consistent, machine-readable** error responses; you need to **never leak a stack trace** (which exposes internals). The clean pattern: services raise **domain exceptions**, and a small set of **handlers** turn them into uniform JSON — so error-building never clutters your routes.

---

## Domain exceptions (raised by services)

Define errors by *meaning*, each carrying its HTTP status and a machine code:

```python
# app/core/exceptions.py
class AppError(Exception):
    status_code = 400
    code = "bad_request"
    def __init__(self, detail: str):
        self.detail = detail

class NotFoundError(AppError):        status_code, code = 404, "not_found"
class PermissionDeniedError(AppError): status_code, code = 403, "permission_denied"
class ConflictError(AppError):        status_code, code = 409, "conflict"
class AuthError(AppError):            status_code, code = 401, "unauthorized"
```

Services raise these — they never build HTTP responses:

```python
if project is None:
    raise NotFoundError("Project not found.")          # service, not route
```

This keeps business logic framework-agnostic: a service doesn't import FastAPI or know what a "404" is — it knows the *domain* concept "not found."

---

## One handler → consistent JSON

Register a handler that maps any `AppError` to a uniform response shape:

```python
# app/core/exceptions.py
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle(request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "detail": exc.detail}},
        )
```

Now *every* domain error comes back in the same shape, with the right status:

**Output (real run, duplicate registration):**
```json
409  {"error": {"code": "conflict", "detail": "A user with this email already exists."}}
```
**Output (real run, accessing another user's project):**
```json
403  {"error": {"code": "permission_denied", "detail": "You do not have access to this project."}}
```

Consumers can branch on the stable `code`; humans read `detail`. Routes stay clean — they just call services and let raised exceptions become responses.

---

## The three error sources

| Source | Example | Who returns it |
|--------|---------|----------------|
| **Validation** | bad request body | FastAPI/Pydantic → automatic **422** |
| **Domain** | not found, forbidden, conflict | your `AppError` handler |
| **Unexpected** | a bug, a downed dependency | a catch-all → **500** (no details leaked) |

Validation is free (Pydantic, [03-1](../03_schemas_and_crud/01_pydantic_schemas.md)). Domain errors are the handler above. For the third, FastAPI already returns a bare `500` without your stack trace — but log the exception server-side (with the request id, [08-1](../08_observability_and_ops/01_structured_logging.md)) so *you* can debug it while the client sees nothing sensitive.

> ⚠️ **Never return exception text to clients on a 500.** `str(exc)` can contain a SQL query, a file path, or a secret. Return a generic message publicly; log the details privately. The domain errors above are *safe* messages you wrote on purpose — that's the difference.

---

## Recap & next

- ✅ Services raise **domain exceptions** (`NotFoundError`, `PermissionDeniedError`, …) carrying status + code.
- ✅ One **handler** maps them to a uniform `{"error": {"code", "detail"}}` JSON — routes stay clean.
- ✅ Three sources: validation (auto 422), domain (your handler), unexpected (500, log privately, leak nothing).
- ✅ Machine-readable `code` for clients, `detail` for humans.
- ✅ Self-check: why should a service raise `NotFoundError` instead of FastAPI's `HTTPException`?

→ Next: **[05-3 · Middleware & CORS](03_middleware_and_cors.md)**

## Exercises

1. Add a `ValidationConflictError` (422) subclass and raise it from a service when, say, a task's `assignee_id` isn't a member of the project. Confirm it returns your uniform shape.

<details>
<summary>Solution</summary>

Subclass `AppError` with `status_code = 422, code = "invalid"`. Raise it in `TaskService` when the assignee check fails. Because it's an `AppError`, the existing handler formats it — no new handler needed. That extensibility is the payoff of one base class + one handler.
</details>
