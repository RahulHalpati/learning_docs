# 02-2 · Engine & session

> **Level:** Intermediate · **Prerequisites:** [02-1 · SQLAlchemy models](01_sqlalchemy_models.md)
> **Time:** 35 min · **Verified:** 2026-07-27 (SQLAlchemy 2.0.51, aiosqlite/asyncpg)

## Why this matters

The **engine** owns the connection pool (created once per process); a **session** is a unit of work for one request (created per request). Getting this right — one engine, a fresh session per request, commit on success / rollback on error — is the difference between a service that handles load and one that leaks connections or corrupts data.

---

## Engine + session factory

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

# ONE engine per process — it holds the connection pool.
engine = create_async_engine(settings.database_url, echo=settings.debug, future=True)

# A factory that produces sessions. expire_on_commit=False lets you read attributes
# on returned objects after commit (needed when serializing the response).
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
```

- **`create_async_engine`** — async engine. The URL's driver (`+aiosqlite` / `+asyncpg`) makes it async.
- **One engine, forever** — never create an engine per request; the pool is the whole point.
- **`expire_on_commit=False`** — so response serialization can still read the object's attributes after the session commits.

---

## The `get_db` dependency

Each request gets its own session via a FastAPI dependency that commits on success and rolls back on failure:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()          # request succeeded → persist
        except Exception:
            await session.rollback()        # something failed → undo
            raise
```

Endpoints (and services) receive it by declaring `db: AsyncSession = Depends(get_db)`. Two rules this enforces:

- **One session per request.** Never share a session across requests or store it globally — sessions aren't concurrency-safe.
- **Atomic per request.** Either all the request's writes commit together, or none do. A failed request never leaves half-written data.

> **Tip — where's the commit?** We commit in the dependency, *after* the endpoint returns. So services and repositories `flush()` (to get generated ids) but don't `commit()` — the request's outcome decides that. One clear commit point per request beats commits scattered through business logic.

---

## Using it (typed alias)

To avoid repeating `Depends(get_db)` everywhere, alias it:

```python
# app/api/deps.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]
```

Now any endpoint just writes `db: DbSession` and gets a per-request session. Clean and consistent.

---

## async all the way

Because the engine, sessions, and driver are async, your repositories `await` their queries and your endpoints are `async def`. This is what lets one worker handle many concurrent requests while they wait on the database — the payoff of the async foundation (covered deeply in the [async course](../../fastapi_async_websockets/01_async_python/README.md)). A blocking, synchronous DB call in an async endpoint would stall the whole event loop.

---

## Recap & next

- ✅ **One engine per process** (owns the pool); **one session per request** (a unit of work).
- ✅ `get_db` yields a session and **commits on success / rolls back on error** — atomic requests.
- ✅ Services/repositories `flush()`; the dependency owns the single `commit()`.
- ✅ Alias it as `DbSession` for clean injection.
- ✅ Self-check: why commit in the `get_db` dependency rather than inside each service method?

→ Next: **[02-3 · Migrations with Alembic](03_migrations_alembic.md)**

## Exercises

1. Temporarily set `DEBUG=true` and hit an endpoint; observe SQLAlchemy echo the SQL. Why is `echo` tied to a setting rather than always on?

<details>
<summary>Solution</summary>

`echo=settings.debug` logs every statement — invaluable locally, noisy and a minor perf cost in production. Tying it to `DEBUG` means you flip SQL logging with an env var, never a code change, and it's off by default in prod.
</details>
