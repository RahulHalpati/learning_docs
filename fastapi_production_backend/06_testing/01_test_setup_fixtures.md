# 06-1 · Test setup & fixtures

> **Level:** Intermediate · **Prerequisites:** [02-2 · Engine & session](../02_data_layer/02_engine_and_session.md)
> **Time:** 40 min · **Verified:** 2026-07-27 (pytest 9.1.1, pytest-asyncio 1.4.0, httpx 0.28.1)

## Why this matters

Good tests are **fast, isolated, and realistic**: each test starts from a clean database, runs against the *real* app (routers, deps, serialization), and needs no external services. The setup that delivers this — an in-memory DB, a dependency override, and an httpx client over the ASGI app — is worth getting right once; then every test is easy.

---

## Config: async mode

```ini
# pytest.ini
[pytest]
asyncio_mode = auto           # treat `async def test_*` as async tests, no decorator needed
```

With `asyncio_mode = auto`, any `async def test_...` just runs. Install `pytest-asyncio`.

---

## The `client` fixture — real app, throwaway DB

The key moves: a fresh **in-memory SQLite** per test, override `get_db` to use it, and drive the app with httpx's `ASGITransport` (no network, no running server):

```python
# tests/conftest.py (essentials)
import app.models                       # register models before the app imports
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app

@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool,
                                 connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)     # fresh schema
    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():                          # same commit/rollback contract
        async with TestSession() as s:
            try:
                yield s; await s.commit()
            except Exception:
                await s.rollback(); raise

    fastapi_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=fastapi_app),
                           base_url="http://test") as c:
        yield c
    fastapi_app.dependency_overrides.clear()
    await engine.dispose()
```

Three ideas make this work:

- **In-memory SQLite + `StaticPool`** — a single shared connection means all sessions in a test see the same database; it vanishes when the test ends. Fast and perfectly isolated.
- **`dependency_overrides[get_db]`** — FastAPI's built-in seam: swap the real database for the test one *without touching app code*. This is why `get_db` being a dependency (02-2) matters.
- **`ASGITransport`** — httpx talks to the app object directly, in-process. Real routing, real middleware, real serialization — no server, no sockets.

---

## The `auth_client` fixture — logged in

Most routes need auth, so build a fixture that's already registered and carrying a token:

```python
@pytest_asyncio.fixture
async def auth_client(client):
    await client.post("/api/v1/auth/register", json={
        "email": "user@example.com", "password": "password123", "full_name": "Test User"})
    tokens = (await client.post("/api/v1/auth/login", data={
        "username": "user@example.com", "password": "password123"})).json()
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return client
```

Now a test that needs a logged-in user just asks for `auth_client` — no auth boilerplate per test. Fixtures compose: `auth_client` builds on `client`.

> **Tip — SQLite for tests, Postgres in prod.** In-memory SQLite makes the suite start instantly and run anywhere (CI included). For features that depend on Postgres-specific behavior, run a subset against a disposable Postgres (a Docker service in CI). Most CRUD/auth logic is database-agnostic and SQLite covers it fine.

---

## Recap & next

- ✅ `asyncio_mode = auto` + `pytest-asyncio` runs async tests with no decorators.
- ✅ A `client` fixture: fresh in-memory DB (`StaticPool`) + `dependency_overrides[get_db]` + httpx `ASGITransport`.
- ✅ `auth_client` layers a registered, logged-in user on top — fixtures compose.
- ✅ Tests are fast, isolated, and hit the **real** app; SQLite covers most logic, Postgres for its specifics.
- ✅ Self-check: why does overriding `get_db` require no changes to the application code?

→ Next: **[06-2 · Writing API tests](02_writing_api_tests.md)**

## Exercises

1. Add a `session` fixture that yields a raw `AsyncSession` on the test DB, so you can unit-test a *service* (e.g. `ProjectService`) without going through HTTP.

<details>
<summary>Solution</summary>

Refactor the engine/session setup into a fixture that yields `TestSession()`. A service test then does `svc = ProjectService(session); await svc.create(...)` and asserts on the returned object — testing business logic directly, no client needed. The layered design makes this trivial.
</details>
