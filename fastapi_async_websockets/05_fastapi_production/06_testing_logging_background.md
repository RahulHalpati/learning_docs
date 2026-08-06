# 06: Testing, logging & background tasks

> **Level:** Intermediate · **Prerequisites:** [02 · Dependency injection](02_dependency_injection.md), [01 · Project structure](01_project_structure.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-03 (FastAPI 0.136.1, pytest 9.0.3)

## Why this matters

The difference between a hobby script and a professional service is the stuff *around* the code: a test suite that catches regressions, logs that let you debug production, and a way to do slow work without making users wait. This module covers all three with the idiomatic FastAPI tools — `pytest` + `TestClient`, the `logging` module, and `BackgroundTasks`.

## Concept: testing with `pytest` + `TestClient`

`pytest` is the de-facto Python test framework. Combined with FastAPI's `TestClient` (which calls your app in-process — no server needed), you write fast, reliable tests. Test functions are named `test_*` and use plain `assert`:

```python
# tests/test_items.py
from fastapi.testclient import TestClient
from app.main import app          # your real app

client = TestClient(app)

def test_list_items():
    response = client.get("/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_missing_item_404():
    response = client.get("/items/99999")
    assert response.status_code == 404
    assert response.json()["detail"]      # there's an error message
```

Run it:

```bash
pip install pytest
pytest -q
```

pytest discovers every `test_*` function, runs it, and reports pass/fail. Each `assert` that fails shows you exactly what was expected vs. got.

## Concept: fixtures — reusable test setup

A **fixture** is setup shared across tests (a client, a database, test data). Declare it once with `@pytest.fixture` and tests receive it by naming it as a parameter:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    # 'with' runs the app's lifespan (startup/shutdown) around the tests
    with TestClient(app) as c:
        yield c                  # the test runs here; teardown happens after

def test_health(client):         # pytest injects the fixture by name
    assert client.get("/health").status_code == 200
```

Using `with TestClient(app) as c:` matters when your app has a **lifespan** ([02.03](../02_fastapi_basics/03_calling_apis_async.md)) — it ensures startup/shutdown run. Common fixtures live in a `conftest.py` so every test file can use them without importing.

## Concept: overriding dependencies in tests

This is where Module 02's DI pays off. Swap real dependencies (DB, settings, auth) for fakes via `app.dependency_overrides`, ideally in a fixture that cleans up after itself:

```python
import pytest
from app.main import app
from app.api.deps import get_db

@pytest.fixture
def client_with_fake_db():
    def fake_db():
        return {"1": "TEST-ITEM"}
    app.dependency_overrides[get_db] = fake_db    # inject the fake
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()              # ALWAYS reset, or it leaks to other tests
```

Now tests run against a deterministic in-memory fake — fast, isolated, no real database. The `clear()` in teardown prevents the override leaking into the next test.

## Concept: parametrized tests

To run the same test over many inputs, use `@pytest.mark.parametrize` instead of copy-pasting:

```python
import pytest

@pytest.mark.parametrize("item_id,expected_status", [(1, 200), (2, 200), (99999, 404)])
def test_item_statuses(client, item_id, expected_status):
    assert client.get(f"/items/{item_id}").status_code == expected_status
```

This becomes **three** separate test cases, each reported individually.

## Verified: a real pytest run

Here's a self-contained app plus its test suite — fixtures, dependency override, and parametrize — run with real `pytest`:

```python
# test_app_demo.py  (run with:  pytest -q test_app_demo.py)
from typing import Annotated
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

# --- a small app ---
def get_db():
    return {1: "apple", 2: "banana"}

DB = Annotated[dict, Depends(get_db)]
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/items/{item_id}")
async def get_item(item_id: int, db: DB):
    if item_id not in db:
        raise HTTPException(404, detail="not found")
    return {"id": item_id, "name": db[item_id]}

# --- fixtures ---
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def client_fake_db():
    app.dependency_overrides[get_db] = lambda: {1: "TEST-ITEM"}
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- tests ---
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}

@pytest.mark.parametrize("item_id,expected", [(1, 200), (2, 200), (99, 404)])
def test_item_statuses(client, item_id, expected):
    assert client.get(f"/items/{item_id}").status_code == expected

def test_override(client_fake_db):
    # with the fake db, item 1 is TEST-ITEM and item 2 no longer exists
    assert client_fake_db.get("/items/1").json()["name"] == "TEST-ITEM"
    assert client_fake_db.get("/items/2").status_code == 404
```

**Verified output** (`pytest -q`):

```
.....                                                                    [100%]
5 passed in 0.31s
```

Five test cases (1 health + 3 parametrized + 1 override) all pass. The override fixture gave one test a fake DB without touching the others.

## Concept: async tests (when you need them)

`TestClient` is synchronous and covers most cases. To test concurrent async behavior directly, drive the app with `httpx.AsyncClient` over an **ASGI transport** (no network):

```python
# illustrative — under pytest this needs `pip install pytest-asyncio` and @pytest.mark.asyncio
import httpx

async def call_health():
    transport = httpx.ASGITransport(app=app)            # talk to the app in-process
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
        return response.json()
```

The mechanism (`ASGITransport` + `AsyncClient`) is verified below; wiring it into pytest just needs the `pytest-asyncio` plugin so `async def test_...` functions run.

## Concept: logging (not `print`)

`print` has no levels, no timestamps, and no routing — never use it for a real service. Use the standard **`logging`** module: get a logger per module, and let your entry point configure handlers/levels once.

```python
# anywhere in the app
import logging
logger = logging.getLogger(__name__)      # a named logger, per module

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    logger.info("fetching item %s", item_id)        # %s lazy-formatting: cheap if filtered out
    if item_id not in ITEMS:
        logger.warning("item %s not found", item_id)
        raise HTTPException(404, "not found")
    return ITEMS[item_id]
```
```python
# app/main.py — configure logging once, at startup
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
```

Best practices:

- **One logger per module** via `logging.getLogger(__name__)` — the name tells you where a line came from.
- **Levels**: `DEBUG` (dev detail), `INFO` (normal events), `WARNING` (unexpected but handled), `ERROR` (failed operation), `CRITICAL`. Filter by level per environment (DEBUG locally, INFO in prod).
- **Lazy `%s` formatting** (`logger.info("x=%s", x)`, not f-strings) so the string is only built if the line is actually emitted.
- **Never log secrets** (passwords, tokens, full request bodies). Pair with `SecretStr` (Module 03).
- **Structured/JSON logs** in production (via a library like `structlog` or a JSON formatter) so log aggregators can parse fields — pair each line with the `request_id` from Module 05's middleware for tracing.
- Uvicorn has its own loggers (`uvicorn.access`, `uvicorn.error`); in production you typically configure logging via a dict/file so your app and Uvicorn agree on format.

## Concept: `BackgroundTasks` — work after the response

Some work shouldn't make the user wait: sending an email, writing an audit log, invalidating a cache. `BackgroundTasks` runs it **after the response is sent**:

```python
from fastapi import BackgroundTasks

def send_welcome_email(address: str):
    ...  # slow-ish; the user shouldn't wait for it

@app.post("/signup")
async def signup(email: str, background_tasks: BackgroundTasks):
    # ... create the user ...
    background_tasks.add_task(send_welcome_email, email)   # queued, runs after responding
    return {"status": "created"}                            # returns immediately
```

The client gets `{"status": "created"}` right away; `send_welcome_email` runs afterward. 

> **Scope:** `BackgroundTasks` is for short, in-process work. For anything heavy, retryable, or long-running (video processing, big batch jobs), use a real task queue (Celery, Dramatiq, ARQ) — a background task runs in the same process and isn't durable if the server restarts.

## Verified: background task + async ASGI client

```python
# bg_async_demo.py
import asyncio
import httpx
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()
side_effects = []                       # observe that the task ran

def record(msg: str):
    side_effects.append(msg)

@app.post("/notify")
async def notify(background_tasks: BackgroundTasks):
    background_tasks.add_task(record, "notified")   # runs after the response
    return {"queued": True}

@app.get("/health")
async def health():
    return {"status": "ok"}

async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        health = await ac.get("/health")
        print("async client GET /health ->", health.json())
        resp = await ac.post("/notify")
        print("POST /notify ->", resp.json())
    # background task has run by the time the request fully completes:
    print("side effects after request ->", side_effects)

asyncio.run(main())
```

**Verified output:**

```
async client GET /health -> {'status': 'ok'}
POST /notify -> {'queued': True}
side effects after request -> ['notified']
```

The async ASGI client called the app with no network; the endpoint returned immediately; and the background task ran (the `side_effects` list got `"notified"`) after the response.

## Common mistakes

**Mistake: forgetting to clear `dependency_overrides`.** An override left set leaks into later tests, causing spooky failures. Clear it in fixture teardown.

**Mistake: tests that hit real external services / DBs.** Slow, flaky, and they mutate real state. Override those dependencies with fakes (Module 02).

**Mistake: `print` for logging.** No levels, no timestamps, can't be routed or silenced. Use `logging`.

**Mistake: building log strings eagerly.** `logger.debug(f"payload={huge}")` builds the string even when DEBUG is off. Use `logger.debug("payload=%s", huge)`.

**Mistake: heavy/durable work in `BackgroundTasks`.** It's in-process and not retried on crash. Use a task queue for important or long jobs.

## Practice

**Exercise:** Write a parametrized test that checks three different `X-API-Key` header values against a protected endpoint: a valid key → 200, a wrong key → 401, and no key → 401. (Reuse the `require_api_key` dependency idea from [Module 05](05_security_and_middleware.md).)

<details><summary>Solution</summary>

```python
import pytest
from fastapi.testclient import TestClient
# assume `app` has GET /keyed protected by require_api_key expecting "expected-secret-key"

client = TestClient(app)

@pytest.mark.parametrize("headers,expected", [
    ({"X-API-Key": "expected-secret-key"}, 200),
    ({"X-API-Key": "wrong"}, 401),
    ({}, 401),                                   # missing key
])
def test_api_key(headers, expected):
    assert client.get("/keyed", headers=headers).status_code == expected
```

Three cases from one test. Note both "wrong" and "missing" are `401` in this FastAPI version (see Module 05's version note). (Verified.)
</details>

## Recap & next

- ✅ Test with **`pytest` + `TestClient`**; use **fixtures** for shared setup and **`@pytest.mark.parametrize`** for many inputs.
- ✅ Swap real dependencies for fakes via **`app.dependency_overrides`** in a fixture — and **clear** it in teardown.
- ✅ For direct async tests, drive the app with **`httpx.AsyncClient` + `ASGITransport`** (add `pytest-asyncio` to run `async def` tests).
- ✅ Use the **`logging`** module (one logger per module, levels, lazy `%s`, never secrets) — not `print`.
- ✅ Offload short after-response work with **`BackgroundTasks`**; use a real queue for heavy/durable jobs.
- Self-check: why must a test fixture that sets `dependency_overrides` also clear it?

🎉 **Section 05 complete.** You can now structure, inject into, configure, error-handle, secure, and test a FastAPI service the way professionals do.

→ Back to the [Section 05 index](README.md) · the [course index](../README.md) · or build the [AI chat project](../99_project_streaming_chat.md) applying these patterns.
