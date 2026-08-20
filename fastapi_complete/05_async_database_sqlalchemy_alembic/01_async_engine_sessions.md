# 05-1 · Async engine & sessions

> **Level:** Intermediate · **Prerequisites:** [04 · Dependency injection & app structure](../04_dependency_injection_app_structure/README.md)
> **Time:** ~40 min · **Verified:** 2026-08-07 (SQLAlchemy 2.0 · asyncpg · Alembic · PostgreSQL 16)

## Why this matters

A database call is mostly *waiting* — the query travels over the network, Postgres works, the rows travel back. With a sync driver, the worker thread blocks for that whole round trip; with an async driver, the event loop parks the request at the `await` and serves others in the meantime. That's why one async worker can hold hundreds of in-flight requests where a sync worker holds one. The plumbing that makes this safe — **one engine per process, one session per request, one commit point** — is what this lesson builds, and getting it wrong is how services leak connections or half-commit data under load.

---

## The engine: one per process

The engine owns the **connection pool**. Opening a Postgres connection costs a TCP handshake, auth, and backend startup — far too expensive per request. The pool opens a handful once and lends them out.

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# ONE engine per process. Module level = created once at import.
engine = create_async_engine(
    settings.database_url,   # postgresql+asyncpg://linkbox:linkbox@localhost:5432/linkbox
    echo=settings.debug,     # log SQL in dev, silent in prod
    pool_size=5,             # connections kept open permanently
    max_overflow=10,         # extra connections under burst, closed when idle again
    pool_pre_ping=True,      # test each connection before lending it out
)
```

- **`+asyncpg` in the URL** is what makes the engine async — asyncpg is the fast, native-async Postgres driver.
- **`pool_size` + `max_overflow`** cap total connections at 15 here. Postgres defaults to ~100 max connections *total* — if you run 8 workers, budget accordingly. When all 15 are busy, the 16th request **queues** (default 30 s, then `TimeoutError`) — a queue under load beats exhausting the database.
- **`pool_pre_ping=True`** sends a cheap `SELECT 1` before handing out a pooled connection. Networks drop idle TCP connections (firewalls, load balancers, Postgres restarts); without pre-ping, the *next request* after an idle period crashes with a stale-connection error. Pre-ping turns that crash into a transparent reconnect.
- **Never create an engine per request.** You'd pay the full connection handshake every time and defeat the pool entirely. One module-level engine, forever.

---

## The session factory

A **session** is a unit of work: it tracks the objects you load and change, and turns them into SQL at flush/commit. Sessions are cheap — one per request; the factory stamps them out:

```python
# app/db/session.py (continued)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

Why **`expire_on_commit=False`**: by default, commit *expires* every loaded object — the next attribute access triggers a refresh query. In async code that refresh is a lazy load happening after your endpoint returned, outside any `await` — it raises `MissingGreenlet` (much more on this in 05-2). Since the typical web flow is *load → commit → serialize the response*, we keep attributes readable after commit. The trade-off: you might serialize slightly stale data if something else changed the row mid-request — irrelevant for the standard request/response pattern.

---

## The `get_db` dependency

Each request gets a fresh session from a yield dependency — the same pattern you used for resources in Section 04, now doing real transactional work:

```python
# app/db/session.py (continued)
from collections.abc import AsyncGenerator


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session               # endpoint runs here
            await session.commit()      # endpoint succeeded → persist everything
        except Exception:
            await session.rollback()    # endpoint raised → undo everything
            raise
```

Two guarantees this structure enforces:

- **One session per request, never shared.** Sessions are not concurrency-safe; a global session shared across requests corrupts state. The dependency scopes it to exactly one request.
- **Atomic requests.** All of a request's writes commit together after the endpoint returns, or none do. A request that fails halfway leaves zero rows behind.

> **Tip — the single commit point.** Notice where `commit()` lives: in the dependency, *not* in endpoints or services. Business code calls `await session.flush()` when it needs generated ids mid-request, but never commits — the request's overall success decides that, in exactly one place. Commits scattered through business logic mean a request can fail *after* some of its data is already permanent — the classic half-written-order bug.

---

## The `DbSession` alias

Typing `db: AsyncSession = Depends(get_db)` in every endpoint gets old. Alias it once:

```python
# app/api/deps.py
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]
```

```python
@router.get("/links/{slug}")
async def get_link(slug: str, db: DbSession):   # that's it
    ...
```

---

## Engine disposal in lifespan

The engine is created at import; shut it down cleanly when the process stops, so pooled connections close instead of Postgres logging aborted connections on every deploy:

```python
# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield                     # app serves requests
    await engine.dispose()    # shutdown: close all pooled connections cleanly


app = FastAPI(lifespan=lifespan)
```

---

## Recap & next

- ✅ Async DB access lets one worker serve many requests *while* they wait on Postgres — the event loop parks them at `await`.
- ✅ **One engine per process** (owns the pool: `pool_size`, `max_overflow`, `pool_pre_ping` against stale connections).
- ✅ **One session per request** via the `get_db` yield dependency — commit on success, rollback on error, **one commit point**.
- ✅ `expire_on_commit=False` keeps objects readable for response serialization after commit.
- ✅ `DbSession` alias for clean injection; `engine.dispose()` in lifespan for clean shutdown.
- ✅ Self-check: a teammate adds `await session.commit()` inside a service method "so the data saves sooner." What bug did they just create?

→ Next: **[05-2 · Models & relationships](02_models_and_relationships.md)**

## Exercises

1. Set `pool_size=1, max_overflow=0`, add `await asyncio.sleep(2)` inside an endpoint (after a query), and fire 5 concurrent requests (`httpx` or a shell loop). What happens, and why is this behavior *better* than letting every request open its own connection?

<details>
<summary>Solution</summary>

The first request takes the only connection; the other four queue at the pool. Each proceeds as the connection frees; any that queue past `pool_timeout` (30 s default) raise `TimeoutError`. This is backpressure: the pool caps what your process can throw at Postgres. Uncapped per-request connections would instead exhaust Postgres's global `max_connections`, taking down *every* service sharing that database — a bounded queue in one process is the far cheaper failure.
</details>

2. Temporarily set `expire_on_commit=True` in the factory and hit an endpoint that returns a created object. Explain the error you see.

<details>
<summary>Solution</summary>

`MissingGreenlet` (or a similar sync-in-async error). Commit expired the object, so serializing the response touches expired attributes, which triggers a refresh — a database query — after the endpoint already returned, outside any `await` point where the async session could run I/O. `expire_on_commit=False` avoids the refresh entirely by keeping loaded attribute values after commit.
</details>

3. Why does `get_db` re-`raise` after rollback instead of swallowing the exception?

<details>
<summary>Solution</summary>

Rollback is about the *database* (undo the writes); the exception still needs to reach FastAPI's exception handlers so the client gets the right error response (a 500, or whatever a matching handler produces). Swallowing it would return a 200 with a broken or empty body for a request whose work was just rolled back — the worst of both worlds.
</details>
