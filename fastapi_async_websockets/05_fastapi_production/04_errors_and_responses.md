# 04: Errors, status codes & response design

> **Level:** Intermediate · **Prerequisites:** [02 · Dependency injection](02_dependency_injection.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-03 (FastAPI 0.136.1, Pydantic 2.12.3)

## Why this matters

An API is a contract. Clients depend on **which status code** you return, **what shape** success looks like, and **what an error looks like**. Sloppy APIs return `200` with `{"error": "..."}` inside, or leak stack traces, or use inconsistent error formats. This module covers the professional approach: correct status codes, typed responses, validated inputs, and a single consistent error format.

## Concept: HTTP status codes that mean something

Use the status code to signal the outcome — clients (and browsers, caches, monitoring) rely on it:

| Code | Meaning | When |
|------|---------|------|
| `200 OK` | success | normal GET/PUT response |
| `201 Created` | resource created | successful POST that makes something |
| `204 No Content` | success, empty body | successful DELETE |
| `400 Bad Request` | client sent something invalid (semantically) | business-rule violation |
| `401 Unauthorized` | not authenticated | missing/invalid credentials |
| `403 Forbidden` | authenticated but not allowed | lacks permission |
| `404 Not Found` | resource doesn't exist | unknown id |
| `409 Conflict` | conflicts with current state | duplicate email |
| `422 Unprocessable Entity` | request failed **validation** | FastAPI's automatic Pydantic errors |
| `500 Internal Server Error` | your bug | uncaught exception |

FastAPI gives you a `status` module with named constants — use them instead of bare numbers for readability:

```python
from fastapi import status
status.HTTP_201_CREATED        # == 201, but self-documenting
status.HTTP_404_NOT_FOUND      # == 404
```

## Concept: raising errors with `HTTPException`

To return an error, **raise** `HTTPException`. FastAPI turns it into a proper JSON error response with the right status code:

```python
from fastapi import FastAPI, HTTPException, status

app = FastAPI()
ITEMS = {1: "apple", 2: "banana"}

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )
    return {"id": item_id, "name": ITEMS[item_id]}
```

`GET /items/99` → status **404**, body `{"detail": "Item 99 not found"}`. You `raise` from anywhere — including deep inside a service or dependency — and FastAPI handles it. Don't `return` error dicts with a 200; raise the exception with the right code.

## Concept: success responses — status code & response model

Declare the **success** status code per route, and type the output with `response_model` ([02.02](../02_fastapi_basics/02_params_and_models.md)) so the contract is explicit and secrets are filtered:

```python
from pydantic import BaseModel

class ItemIn(BaseModel):
    name: str

class ItemOut(BaseModel):
    id: int
    name: str

@app.post("/items", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemIn):
    new_id = max(ITEMS) + 1 if ITEMS else 1
    ITEMS[new_id] = item.name
    return {"id": new_id, "name": item.name}   # validated & shaped by ItemOut, returned as 201
```

A successful `POST /items` returns **201** (not 200) with a body matching `ItemOut`. Using request/response models on both ends makes the API self-documenting in `/docs` and stops internal fields from leaking.

## Concept: a consistent error format with custom exception handlers

By default FastAPI errors look like `{"detail": "..."}`. Many teams want a **uniform error envelope** across the whole API (easier for clients to parse, nicer for logging). You define your own exception type and register a handler that formats it:

```python
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Domain error with an HTTP status, a stable code, and a message."""
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    # one consistent shape for every domain error in the app
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
```

Now anywhere in the app you `raise AppError(404, "item_not_found", "Item 99 not found")` and every client gets the same envelope: `{"error": {"code": "...", "message": "..."}}`. The **stable `code`** (e.g. `"item_not_found"`) is something clients can branch on without parsing human text.

## Concept: customizing validation (422) errors

FastAPI's automatic validation errors are `422` with a detailed list. To make them match your envelope too, override the `RequestValidationError` handler:

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "details": exc.errors()}},
    )
```

Now even framework-level validation failures come back in your house style.

## Concept: richer input validation with `Field` and validators

Push validation into the model so bad data is rejected automatically (before your code runs). Use `Field` for constraints and `field_validator` for custom rules:

```python
from pydantic import BaseModel, Field, field_validator, EmailStr

class SignupIn(BaseModel):
    email: EmailStr                               # validated email format
    name: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=0, le=130)                # 0..130 inclusive
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if v.isalpha():                           # custom rule: must not be all letters
            raise ValueError("password must contain a non-letter character")
        return v
```

- **`Field(min_length=…, ge=…, le=…)`** adds constraints that show up in `/docs` and produce `422` on violation.
- **`EmailStr`** validates email format (needs the `email-validator` package, included with `fastapi[standard]`).
- **`@field_validator`** runs your own check; raising `ValueError` becomes a clean `422` field error.

## Verified: status codes, custom errors, and validation together

```python
# errors_demo.py
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, field_validator

app = FastAPI()
ITEMS = {1: "apple"}

class AppError(Exception):
    def __init__(self, status_code, code, message):
        self.status_code, self.code, self.message = status_code, code, message

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"code": exc.code, "message": exc.message}})

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422,
                        content={"error": {"code": "validation_error",
                                           "fields": [e["loc"][-1] for e in exc.errors()]}})

class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=20)

    @field_validator("name")
    @classmethod
    def no_digits(cls, v):
        if any(c.isdigit() for c in v):
            raise ValueError("name cannot contain digits")
        return v

class ItemOut(BaseModel):
    id: int
    name: str

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Item {item_id} not found")
    return {"id": item_id, "name": ITEMS[item_id]}

@app.post("/items", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemIn):
    new_id = max(ITEMS) + 1
    ITEMS[new_id] = item.name
    return {"id": new_id, "name": item.name}

@app.get("/widgets/{wid}")
async def get_widget(wid: int):
    raise AppError(404, "widget_not_found", f"No widget {wid}")   # custom envelope

c = TestClient(app)
print("404 (HTTPException)   ->", c.get("/items/99").status_code, c.get("/items/99").json())
r = c.post("/items", json={"name": "pear"})
print("create (201 + model)  ->", r.status_code, r.json())
print("validation: too long  ->", c.post("/items", json={"name": "x"*50}).status_code,
                                   c.post("/items", json={"name": "x"*50}).json())
print("validation: has digit ->", c.post("/items", json={"name": "ab1"}).json())
print("custom AppError       ->", c.get("/widgets/7").status_code, c.get("/widgets/7").json())
```

**Verified output:**

```
404 (HTTPException)   -> 404 {'detail': 'Item 99 not found'}
create (201 + model)  -> 201 {'id': 2, 'name': 'pear'}
validation: too long  -> 422 {'error': {'code': 'validation_error', 'fields': ['name']}}
validation: has digit -> {'error': {'code': 'validation_error', 'fields': ['name']}}
custom AppError       -> 404 {'error': {'code': 'widget_not_found', 'message': 'No widget 7'}}
```

Three error styles, all behaving correctly: `HTTPException`'s default `{"detail": ...}`, your custom `AppError` envelope, and validation errors reshaped into the same envelope — plus a `201` with a response-model-shaped body on create.

## Common mistakes

**Mistake: returning errors with a 200.** `return {"error": "not found"}` with status 200 lies to clients, caches, and monitoring. **Raise `HTTPException`** (or your `AppError`) with the right status code.

**Mistake: leaking internals in errors.** Don't put exception messages, SQL, or stack traces in responses — they aid attackers and confuse clients. Log the detail server-side ([Module 06](06_testing_logging_background.md)); return a clean message and a stable `code`.

**Mistake: 200 for a create.** A successful POST that creates a resource should be **201**, often with a `Location` header. Set `status_code=status.HTTP_201_CREATED`.

**Mistake: validating in the handler instead of the model.** Checking `if not item.name: raise ...` by hand duplicates what `Field`/validators do automatically and consistently. Put constraints on the model.

## Practice

**Exercise:** Add `DELETE /items/{item_id}` that returns **204 No Content** on success and raises a 404 (`HTTPException`) if the item doesn't exist. (Hint: a 204 response has no body — return `None` and set `status_code=204`.)

<details><summary>Solution</summary>

```python
from fastapi import Response

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int):
    if item_id not in ITEMS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Item {item_id} not found")
    del ITEMS[item_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)   # explicit empty 204
```

- `DELETE /items/1` → **204** with an empty body.
- `DELETE /items/99` → **404** `{'detail': 'Item 99 not found'}`.

(Verified.) 204 is the conventional success code for a delete with nothing to return.
</details>

## Recap & next

- ✅ Use **meaningful status codes** (`201` create, `204` delete, `404`/`409` etc.) via the `status` constants.
- ✅ **Raise `HTTPException`** for errors — never return error dicts with a 200.
- ✅ Type success responses with **`response_model`** and set **`status_code`** per route.
- ✅ For a uniform API, define a custom error type + **`@app.exception_handler`**, and reshape `RequestValidationError` to match.
- ✅ Push input validation into the model with **`Field`** constraints and **`@field_validator`**.
- Self-check: what status code should a successful POST-that-creates return, and how do you set it?

→ Next: **[05 · Security & middleware](05_security_and_middleware.md)** — authenticate requests and add cross-cutting logic.
