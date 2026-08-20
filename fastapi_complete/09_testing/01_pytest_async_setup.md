# 09-1 · Pytest & async test setup

> **Level:** Intermediate · **Prerequisites:** [08 · Redis: caching, rate limiting & background jobs](../08_redis_caching_jobs/README.md)
> **Time:** ~35 min · **Verified:** 2026-08-07 (pytest · pytest-asyncio · httpx)

## Why this matters

Untested backend code is a liability you deploy on hope. But a *slow or flaky* suite is almost as bad — nobody runs it, so it rots. The setup in this lesson is built for two properties: **fast** (tests call your app in-process, no server, no network) and **deterministic** (one event loop, explicit fixtures, no hidden state). Get the foundation right once and every test you write for the rest of your career on this stack is cheap.

---

## The test pyramid, API edition

Three layers, cheapest and most numerous at the bottom:

| Layer | What it tests | Touches | Speed |
|-------|---------------|---------|-------|
| **Unit** | Service/domain functions: slug generation, password rules, token expiry math | Nothing — pure Python | µs |
| **Integration** | Repositories & queries against a **real database** | Postgres | ms |
| **API-level** | Full request → routing → DI → validation → response, through ASGI | The whole app, in-process | ms |

The API layer is where FastAPI apps get the most value per test: one request exercises routing, dependency injection, Pydantic validation, auth, and serialization together — exactly the wiring that unit tests can't see. So the pyramid for an API service is often more of a **house**: a solid base of unit tests, and a broad API-level floor. What you should have *very few* of: tests that spawn a real uvicorn server and talk TCP. That's an end-to-end smoke test, not your daily suite.

---

## pytest-asyncio: one loop to rule them all

Your app is `async def` all the way down, so tests must be too. **pytest-asyncio** makes pytest run coroutine tests — configure it once in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"                           # every `async def test_*` just runs — no marker on each test
asyncio_default_fixture_loop_scope = "session"  # async fixtures all share ONE event loop...
asyncio_default_test_loop_scope = "session"     # ...and tests run on that same loop
addopts = "-q --strict-markers"
testpaths = ["tests"]
```

- **`asyncio_mode = "auto"`** — without it you'd decorate every single test with `@pytest.mark.asyncio`. Auto mode removes the noise and, more importantly, removes the failure mode where a forgotten marker makes an async test *silently pass without running* (pytest collects the coroutine, never awaits it).
- **`loop_scope` — the one that bites.** asyncio objects are bound to the event loop they were created on. Your DB engine will be a *session-scoped* fixture (created once, lesson 09-2); if it lives on one loop but each test runs on a fresh function-scoped loop, asyncpg greets you with `RuntimeError: Task got Future attached to a different loop`. Pinning **both** fixture and test loop scope to `"session"` means one loop for the whole run — engine, sessions, clients, and tests all share it. Deterministic, and no per-test loop setup cost either.

> A test that genuinely needs its own loop can opt out with `@pytest.mark.asyncio(loop_scope="function")` — rare, and now it's *visible* in the code instead of an invisible default.

---

## httpx AsyncClient + ASGITransport: the app, in-process

FastAPI ships `TestClient` — a synchronous wrapper (built on httpx) that's fine for a quick smoke test in a tutorial. We won't use it: an async app deserves async tests, and mixing a sync client into an async suite means a second event-loop universe you don't control. Instead, `httpx.AsyncClient` with **`ASGITransport`**:

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    # ASGITransport calls the app as a Python object — request bytes never
    # touch a socket. No server to start, no port to collide on, no network flakiness.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

- **In-process** — `await client.get("/links")` invokes the ASGI app directly. What runs: routing, dependencies, validation, middleware, your handlers. What doesn't: uvicorn's HTTP parsing and the TCP stack — which you don't need to re-test; they have their own test suites.
- **Why that's better than spawning uvicorn**: orders of magnitude faster, zero port management, and *debuggable* — a breakpoint inside your endpoint fires in the same process as the test. A stack trace goes straight from the assert to your handler.
- **`base_url="http://test"`** — the requests never leave the process, but httpx still needs a syntactically valid base URL to build requests against; any dummy host works.

---

## Anatomy of a good API test

Every good API test has the same three beats — **arrange** (fixtures do the heavy lifting), **act** (one request), **assert** (status, body, *and* side effect):

```python
# tests/api/test_links.py
async def test_create_link_returns_201_and_persists(client, db_session):
    # Arrange — fixtures already gave us a clean DB and an in-process client
    payload = {"url": "https://example.com", "slug": "my-link"}

    # Act — exactly one request; the thing under test
    resp = await client.post("/links", json=payload)

    # Assert — 1) status, 2) response body...
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "my-link"

    # ...and 3) the side effect. A 201 with nothing persisted is a lie.
    link = await db_session.get(Link, body["id"])
    assert link is not None
```

The third assert is what separates a test from a screenshot. Status and body prove the *response* is right; the side-effect check proves the *system* changed the way the response claims. Asserting all three per test — no more — keeps each test failing for exactly one reason.

---

## Layout & naming discipline

Mirror `app/` inside `tests/` so anyone can find the tests for a module without grepping:

```
tests/
├── conftest.py            # shared fixtures: engine, db_session, client, authed_client
├── unit/
│   └── test_slugs.py      # pure functions from app/services/slugs.py
├── integration/
│   └── test_link_repo.py  # repository queries against real Postgres
└── api/
    ├── test_auth.py       # app/api/auth.py
    └── test_links.py      # app/api/links.py
```

Name tests as **`test_<what>_<condition>_<expectation>`**: `test_create_link_duplicate_slug_returns_409` reads as a sentence and, when it fails in CI, tells you what broke *from the name alone*. `test_links_2` tells you nothing — naming is documentation you get for free.

---

## Recap & next

- ✅ Pyramid for APIs: many **unit** tests, real-DB **integration** tests, a broad **API-level** floor through ASGI — almost never a live server.
- ✅ `asyncio_mode = "auto"` kills marker noise; **session-scoped loop** (fixtures *and* tests) prevents "attached to a different loop" errors.
- ✅ `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` — in-process, fast, debuggable. `TestClient` is the sync/quick option; we stay async.
- ✅ Arrange / act / **assert status + body + side effect**; layout mirrors `app/`; names read as sentences.
- ✅ Self-check: why would a session-scoped async engine fixture crash under function-scoped test loops, and which config line prevents it?

→ Next: **[09-2 · DB fixtures & transaction rollback](02_db_fixtures_rollback.md)**

## Exercises

1. Write `test_get_unknown_slug_returns_404` for `GET /links/{slug}`. Assert the status **and** the error body shape (`detail` key).

<details>
<summary>Solution</summary>

```python
async def test_get_unknown_slug_returns_404(client):
    resp = await client.get("/links/no-such-slug")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Link not found"}
```

Asserting the body pins the *contract*, not just the code path — if someone later changes the error format, a client-breaking change fails a test instead of a customer.
</details>

2. Delete `asyncio_mode = "auto"` from `pyproject.toml` and run one async test **without** a marker. What happens, and why is it worse than an error?

<details>
<summary>Solution</summary>

The test "passes" with a warning: pytest collected the coroutine but never awaited it, so *no assertion ever ran*. A green test that executes nothing is worse than a red one — it manufactures false confidence. `asyncio_mode = "auto"` (plus `--strict-markers`) makes this failure mode impossible.
</details>

3. In one sentence each: name two things `ASGITransport` does **not** exercise, and why that's acceptable for your daily suite.

<details>
<summary>Solution</summary>

It skips uvicorn's HTTP parsing and the OS network stack (sockets, TLS). Acceptable because those layers are third-party code with their own test suites — your suite should test *your* wiring, and a couple of end-to-end smoke tests against a deployed instance cover the rest.
</details>
