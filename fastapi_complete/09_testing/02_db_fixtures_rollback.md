# 09-2 · DB fixtures & transaction rollback

> **Level:** Intermediate · **Prerequisites:** [09-1 · Pytest & async test setup](01_pytest_async_setup.md)
> **Time:** ~50 min · **Verified:** 2026-08-07 (pytest · pytest-asyncio · httpx)

## Why this matters

Database tests have two classic failure modes: tests that **share state** (test A's rows make test B fail — but only in some orders, so it looks "flaky") and tests that are **slow** (drop-and-recreate the schema per test and a 200-test suite takes minutes). The transaction rollback pattern kills both: every test runs inside a transaction that is rolled back in teardown, so isolation is perfect and cleanup costs one `ROLLBACK` — microseconds. This one fixture design is the difference between a suite people run on every save and one they run before release, reluctantly.

---

## Test against real Postgres, not SQLite

The tempting shortcut is `sqlite+aiosqlite:///:memory:` — zero setup. Don't. **Dialects drift**: Postgres `INSERT ... ON CONFLICT` upserts, deferred constraints, `JSONB` operators, and real concurrent-transaction behavior either don't exist or behave differently on SQLite. A test that passes on SQLite proves your code works on a database you don't run in production — the worst kind of green. Say it once, then never argue about it again: **test on the engine you deploy on.** Docker makes it a one-liner:

```yaml
# docker-compose.test.yml
services:
  test-db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: linkbox_test
    ports: ["5433:5432"]                 # 5433 so it never collides with your dev DB
    tmpfs: [/var/lib/postgresql/data]    # RAM-backed storage: fast, and disposable by design
```

`docker compose -f docker-compose.test.yml up -d` once; the suite connects to `localhost:5433`.

---

## The pattern, layer by layer

**One engine per suite** (session-scoped — the pool is expensive, build it once; this is why 09-1 pinned the event-loop scope to `session`), **one transaction per test**:

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.base import Base

TEST_DB_URL = "postgresql+asyncpg://test:test@localhost:5433/linkbox_test"


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)    # start from nothing —
        await conn.run_sync(Base.metadata.create_all)  # schema built once per run
    yield engine
    await engine.dispose()                             # return every pooled connection


@pytest.fixture
async def db_session(engine):
    async with engine.connect() as conn:
        trans = await conn.begin()          # OUTER transaction — will never commit
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session                        # the test (and the app, via override) runs here
        await session.close()
        await trans.rollback()               # everything the test wrote: gone, in microseconds
```

Why each piece exists:

- **`conn.begin()` before the session** — the transaction belongs to the *connection*, opened by the fixture, so the app code inside the test can't end it. The fixture owns the outcome.
- **Session bound to that connection** (`bind=conn`) — every query the test triggers runs inside the outer transaction. The test *sees* its own writes (they're live inside the transaction) but no other test ever does.
- **`rollback()` in teardown** — isolation without cleanup code. No `DELETE FROM users` scripts that drift out of sync with the schema; the database physically discards the work.

Then wire the app to it — upgrade the `client` fixture from 09-1 to override `get_db`:

```python
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.session import get_db


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session                     # the app uses OUR session — no commit here

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)   # always undo — leaked overrides poison later tests
```

Test writes rows through the API, asserts against the same session, teardown rolls it all back. A 200-test suite pays for one schema build and 200 rollbacks.

---

## The commit problem — where the architecture pays off

Wait — production `get_db` **commits** on success. The override doesn't. Doesn't that break the app?

No, and this is Section 05's discipline paying rent: services and repositories **`flush()`, never `commit()`** — the single commit point lives in `get_db`. In tests we override exactly that dependency, so the one `commit()` in the codebase is *overridden away*. Flushes still send SQL (ids get generated, constraints fire, queries see the rows), everything stays inside the outer transaction, and the rollback erases it. If commits were scattered through your business logic, they'd terminate the outer transaction mid-test and this pattern would collapse — one more reason the "one commit point" rule wasn't just aesthetics.

### Advanced variant: code that genuinely commits

Sometimes you must test code that calls `commit()` for real (a CLI command, a worker, legacy code). SQLAlchemy 2.0 has a built-in answer — bind the session with **`join_transaction_mode="create_savepoint"`**:

```python
session = AsyncSession(
    bind=conn,
    join_transaction_mode="create_savepoint",  # session runs in a nested SAVEPOINT
    expire_on_commit=False,
)
```

Under the hood this is the classic `begin_nested()` recipe: the session works inside a **SAVEPOINT**, so `commit()` merely releases the savepoint — and SQLAlchemy immediately opens a fresh one, so the code can commit repeatedly. The *outer* connection transaction is untouched, and the fixture's final `trans.rollback()` still wipes everything. (Older codebases do this manually with an `after_transaction_end` event listener that restarts the savepoint — recognize it on sight, but write the one-liner.) Reach for this only when needed; the plain pattern is simpler and covers an app that follows the flush-don't-commit rule.

---

## Schema: `create_all` locally, Alembic in CI

`Base.metadata.create_all` builds the schema straight from your models — fast and fine on your machine. But production databases are built by **migrations**, and a migration chain can drift from the models (a hand-edited migration, a forgotten autogenerate). So in CI, build the test schema with Alembic instead:

```bash
uv run alembic upgrade head   # CI: the test schema IS the migration chain
uv run pytest
```

One environment variable or fixture switch, and every CI run now also proves your migrations produce the schema your code expects — two birds, zero extra tests.

---

## Factory fixtures, not fixture explosion

You'll need users and links in dozens of tests, each slightly different. Don't mint `user_a`, `user_b`, `user_with_five_links`, ... fixtures — that's an explosion nobody maintains. Make **factories**: fixtures that return an async builder with sensible defaults and keyword overrides:

```python
from app.core.security import hash_password
from app.models import Link, User


@pytest.fixture
def make_user(db_session):
    async def _make(email: str = "user@test.dev", password: str = "s3cret-pass!", **kw):
        user = User(email=email, hashed_password=hash_password(password), **kw)
        db_session.add(user)
        await db_session.flush()       # get the generated id — but stay inside the rollback
        return user
    return _make


@pytest.fixture
def make_link(db_session, make_user):
    async def _make(slug: str = "test-link", url: str = "https://example.com", owner=None, **kw):
        owner = owner or await make_user()   # missing pieces build themselves
        link = Link(slug=slug, url=url, owner_id=owner.id, **kw)
        db_session.add(link)
        await db_session.flush()
        return link
    return _make
```

A test states only what it *cares about* — `await make_link(slug="taken")` — and the factory fills in the rest. Defaults keep tests short; overrides keep them explicit; `flush()` keeps everything inside the transaction.

---

## The `authed_client` fixture

Most link tests need a logged-in user, and there are two ways to get one:

```python
from app.core.security import create_access_token


@pytest.fixture
async def authed_client(client, make_user):
    user = await make_user(email="owner@test.dev")
    token = create_access_token(sub=str(user.id))          # mint directly — no HTTP round-trips
    client.headers["Authorization"] = f"Bearer {token}"
    yield client, user                                     # tests often need the user too
```

- **Mint the token directly** (above): fast — zero extra requests per test — but coupled to your token internals; if the signing scheme changes, this fixture changes too.
- **Register + login through the API**: exercises the real flow, fully decoupled — but adds two requests to *every* authed test.

The pragmatic split: mint directly in the fixture (it serves dozens of tests), and let the **auth test module** cover register → login → refresh through the real endpoints. The flow is tested once, thoroughly; everyone else gets speed.

---

## Recap & next

- ✅ Test on **real Postgres** in Docker — SQLite's dialect drift (upserts, constraints) turns green tests into lies.
- ✅ THE pattern: session-scoped engine → per-test `conn.begin()` → `AsyncSession(bind=conn)` → override `get_db` → **rollback in teardown**. Clean DB per test, milliseconds each.
- ✅ Flush-don't-commit architecture means the single commit point is overridden away; `join_transaction_mode="create_savepoint"` handles code that truly commits.
- ✅ `create_all` locally; **Alembic in CI** so migrations get tested for free.
- ✅ Factory fixtures (`make_user`, `make_link`) with defaults + overrides beat a zoo of one-off fixtures; `authed_client` mints tokens directly and leaves flow-testing to the auth module.
- ✅ Self-check: your teammate adds `await session.commit()` inside a service "to be safe." Which part of the rollback pattern breaks, and what error will the *next* test in the file see?

→ Next: **[09-3 · Mocking, fakes & overrides](03_mocking_and_overrides.md)**

## Exercises

1. Prove isolation: write two tests that each create a user with the **same email** (unique-constrained). Run them in both orders (`pytest-randomly` will oblige). What would happen with a module-scoped `db_session` and no rollback?

<details>
<summary>Solution</summary>

```python
async def test_creates_alice(make_user):
    user = await make_user(email="alice@test.dev")
    assert user.id is not None

async def test_creates_alice_again(make_user):
    user = await make_user(email="alice@test.dev")   # same email — fine!
    assert user.id is not None
```

Both pass in any order: each test's rows die with its rollback, so the unique constraint never sees a duplicate. With a module-scoped session and no rollback, whichever test ran *second* would hit `UniqueViolationError` — a failure caused by ordering, the definition of flaky.
</details>

2. Sabotage drill: change `db_session` to `scope="module"` and delete the rollback. Run the suite twice. Describe the two distinct symptoms you observe and map each back to the fixture change.

<details>
<summary>Solution</summary>

Symptom 1: *order-dependent failures within a module* — rows from earlier tests are visible to later ones (duplicate keys, wrong counts). Cause: one session now spans all tests in the module. Symptom 2: *the second suite run fails differently than the first* — without rollback, data survives the whole run and (since the engine fixture only rebuilds the schema at session start) collides on the next run. Both trace to the same root: teardown no longer discards the test's writes.
</details>

3. Name a specific linkbox behavior whose test would pass on SQLite but lie about production, and say why.

<details>
<summary>Solution</summary>

The click-counter upsert (`INSERT ... ON CONFLICT (slug) DO UPDATE SET clicks = clicks + 1`) is the classic: SQLite's `ON CONFLICT` support and semantics differ from Postgres (and older SQLite versions lack pieces entirely), so a test could pass against a code path or behavior production never executes. Same story for `JSONB` queries and deferred constraint checks — dialect drift means the test certifies the wrong database.
</details>
