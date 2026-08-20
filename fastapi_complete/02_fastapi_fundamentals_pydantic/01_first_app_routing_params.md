# 02-1 · First app, routing & params

> **Level:** Beginner · **Prerequisites:** [01 · Modern Python baseline](../01_modern_python_async/README.md)
> **Time:** ~40 min · **Verified:** 2026-08-07 (FastAPI 0.116 · Pydantic 2.11)

## Why this matters

FastAPI's core idea is that **the type hint is the contract**: one annotation drives request validation, data conversion, response serialization, *and* the interactive docs. Frameworks before it made you write those four things separately, and they drifted apart. Understanding how a hint like `item_id: int` flows through the whole request pipeline is the foundation for everything else in this course.

---

## Install & run with uv

We manage everything with **uv** — project, venv, and dependencies in one tool:

```bash
uv init linkbox && cd linkbox
uv add "fastapi[standard]"   # fastapi + uvicorn + the `fastapi` CLI
```

The `[standard]` extra pulls in uvicorn (the ASGI server) and the `fastapi` CLI. Now the smallest possible app:

```python
# main.py
from fastapi import FastAPI

app = FastAPI(title="linkbox")

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "hello from linkbox"}
```

Run it in development mode:

```bash
uv run fastapi dev main.py
```

`fastapi dev` finds `app`, starts uvicorn with **auto-reload** (edit a file, the server restarts), and serves at `http://127.0.0.1:8000`. In production you'll run `fastapi run` / plain `uvicorn` instead — no reloader. Open `http://127.0.0.1:8000/docs` right now and keep it open for the rest of the lesson.

---

## Path parameters: the type hint validates

A `{name}` segment in the path becomes a function parameter — and its **type annotation** does the work:

```python
@app.get("/items/{item_id}")
async def read_item(item_id: int) -> dict:
    return {"item_id": item_id}
```

- `GET /items/42` → FastAPI converts `"42"` (URLs are strings) to the int `42`.
- `GET /items/abc` → **422 Unprocessable Entity** with a JSON error explaining exactly which field failed and why. You wrote zero validation code — the annotation *is* the validation.

This is the pattern to internalize: you declare what you want, FastAPI enforces it at the edge, and your function body only ever sees clean, correctly-typed data.

---

## Gotcha: route order matters

Routes are matched **in declaration order**, top to bottom. A fixed path that could also match a parameterized one must come *first*:

```python
@app.get("/users/me")               # MUST be declared before /users/{user_id}
async def read_current_user() -> dict:
    return {"user": "the current user"}

@app.get("/users/{user_id}")
async def read_user(user_id: int) -> dict:
    return {"user_id": user_id}
```

Declare them the other way around and `GET /users/me` matches `/users/{user_id}` with `user_id="me"` — which then fails int validation with a confusing 422. This bites everyone once; now it won't bite you.

---

## Query parameters: required, optional, defaults

Function parameters that are *not* in the path become **query parameters**:

```python
@app.get("/links")
async def list_links(
    q: str,                    # no default → REQUIRED (?q=... or 422)
    limit: int = 10,           # default → optional, ?limit=50 overrides
    offset: int = 0,
    active: bool | None = None,  # optional and possibly absent
) -> dict:
    return {"q": q, "limit": limit, "offset": offset, "active": active}
```

The rules are just Python's own rules:

- **No default → required.** FastAPI returns 422 if it's missing — you never write `if q is None: ...` boilerplate.
- **Default → optional.** The default is used when the client omits it.
- **`X | None = None` → truly optional.** Use this when "not provided" is meaningful and distinct from any real value.
- Types convert here too: `?limit=abc` → 422; `?active=true` → the bool `True`.

---

## Request body: a `BaseModel` parameter

Path and query params are fine for small scalar inputs. Structured data (a JSON body) is declared as a **Pydantic model**:

```python
from pydantic import BaseModel

class LinkCreate(BaseModel):
    url: str
    slug: str | None = None      # optional in the JSON body too

@app.post("/links", status_code=201)    # created → 201, not the default 200
async def create_link(payload: LinkCreate) -> dict:
    return {"created": payload.model_dump()}   # v2 spelling — never .dict()
```

How FastAPI decides where a parameter comes from:

- name appears in the path → **path param**
- it's a Pydantic model → **request body** (parsed from JSON, validated, typed)
- otherwise → **query param**

A malformed body — missing `url`, or `slug` of the wrong type — never reaches your function; the client gets a structured 422 listing every problem at once. And note `status_code=201`: the decorator declares the success status, so it shows up in the docs and you don't hand-craft responses.

For error cases *you* detect, raise `HTTPException`:

```python
from fastapi import HTTPException

@app.get("/links/{slug}")
async def get_link(slug: str) -> dict:
    if slug not in {"abc", "def"}:            # stand-in for a real lookup
        raise HTTPException(status_code=404, detail="link not found")
    return {"slug": slug}
```

---

## `/docs`: the payoff of type hints

Visit `http://127.0.0.1:8000/docs`. Every endpoint you wrote is there — parameters, types, required/optional flags, the `LinkCreate` body schema, the 201 status — all **interactive** (Try it out → real requests against your running app).

Nothing was written twice. FastAPI reads your type hints, builds an **OpenAPI schema** from them (see it raw at `/openapi.json`), and Swagger UI renders that schema. This is why the docs never lie: they are *generated from* the same annotations that enforce validation. Change a type, and validation, conversion, and documentation all update together — the contract can't drift from the code.

---

## Recap & next

- ✅ `uv add "fastapi[standard]"` to install; `uv run fastapi dev main.py` to run with reload.
- ✅ Path params: `{item_id}` + `item_id: int` → conversion and validation for free (422 on bad input).
- ✅ Route order matters: fixed paths (`/users/me`) before parameterized ones (`/users/{user_id}`).
- ✅ Query params follow Python defaults: no default = required; `X | None = None` = truly optional.
- ✅ A `BaseModel` parameter = validated JSON body; `status_code=` declares the success code.
- ✅ `/docs` is generated from your type hints via OpenAPI — one source of truth.
- ✅ Self-check: a client calls `GET /items/abc` against `read_item(item_id: int)`. What status and body come back, and how much code did you write to make that happen?

→ Next: **[02-2 · Pydantic v2 deep dive](02_pydantic_v2_deep_dive.md)**

## Exercises

1. Add `GET /links/{slug}/preview` that takes a required query param `format: str` and returns both values. Verify in `/docs` that `format` is marked required, and that omitting it returns a 422.

<details>
<summary>Solution</summary>

```python
@app.get("/links/{slug}/preview")
async def preview_link(slug: str, format: str) -> dict:
    return {"slug": slug, "format": format}
```

`slug` is in the path → path param. `format` isn't, and has no default → required query param. `GET /links/abc/preview` without `?format=` returns 422 with a `missing` error for `format`.
</details>

2. Deliberately declare `/users/{user_id}` *before* `/users/me`, call `GET /users/me`, and explain the exact error you get. Then fix it.

<details>
<summary>Solution</summary>

You get **422**: routes match in declaration order, so `/users/me` hits `/users/{user_id}` first and FastAPI tries `int("me")`, which fails validation — the error says `user_id` is not a valid integer. The fix is purely ordering: declare `@app.get("/users/me")` above `@app.get("/users/{user_id}")`.
</details>

3. Extend `LinkCreate` with `max_clicks: int = 100` and POST a body where `max_clicks` is `"lots"`. Read the 422 response carefully: what three pieces of information does each error object give you?

<details>
<summary>Solution</summary>

```python
class LinkCreate(BaseModel):
    url: str
    slug: str | None = None
    max_clicks: int = 100
```

Each error in `detail` carries: **`loc`** — where the problem is (`["body", "max_clicks"]`), **`msg`** — a human-readable message ("Input should be a valid integer…"), and **`type`** — a machine-readable code (`int_parsing`). Clients can render `msg` to humans and branch on `type` in code.
</details>
