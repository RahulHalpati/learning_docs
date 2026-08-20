# 06-1 · Layers & boundaries

> **Level:** Intermediate · **Prerequisites:** [05 · Async database: SQLAlchemy 2.0 + Alembic](../05_async_database_sqlalchemy_alembic/README.md)
> **Time:** ~40–50 min · **Verified:** 2026-08-07 (FastAPI 0.116 · SQLAlchemy 2.0 · Pydantic 2.11)

## Why this matters

A route handler that parses HTTP, runs queries, and applies business rules is three programs in one function — and you can only test, reuse, or change it as a whole. Layers aren't an aesthetic; each boundary exists because crossing it produces a specific, recurring failure. This lesson names those failures and gives you the minimal three-layer split that prevents them — no more.

---

## The failure you already have

Here's linkbox's create endpoint as most people first write it:

```python
@router.post("/links", status_code=201)
async def create_link(body: LinkCreate, db: DbSession):
    if body.slug:                                             # business rule
        taken = await db.scalar(select(Link).where(Link.slug == body.slug))
        if taken:
            raise HTTPException(status_code=409, detail="slug taken")
        slug = body.slug
    else:                                                     # more business rules
        for _ in range(3):
            slug = secrets.token_urlsafe(4)
            if not await db.scalar(select(Link).where(Link.slug == slug)):
                break
        else:
            raise HTTPException(status_code=500, detail="no free slug")
    link = Link(slug=slug, target_url=str(body.target_url))
    db.add(link)
    return link
```

It works. Now the concrete failures it's storing up:

1. **Untestable rules.** To test "collision retries three times" you need a running app, an HTTP client, and a database seeded with colliding slugs. A five-line rule costs a fifty-line integration test — so it doesn't get tested.
2. **Duplicated logic.** Next month a nightly Arq job also needs to create links. The job can't call this handler (it's welded to `Request` and `HTTPException`), so someone copy-pastes the slug logic. Now the rule lives twice and drifts.
3. **Every change collides here.** Changing the query shape, the retry policy, and the response format all edit the same function. Three unrelated reasons to touch one block of code is how merge conflicts and regressions happen.

Each failure maps to one boundary. That's the whole argument for layers.

---

## The contract of each layer

| Layer | Owns | Speaks | Never contains |
|-------|------|--------|----------------|
| **Router** (`app/api/`) | HTTP in/out: paths, status codes, response models | Pydantic schemas | queries, business rules, `try/except` around logic |
| **Service** (`app/services/`) | business rules, orchestration, domain exceptions | plain Python + ORM objects | `fastapi` imports, `HTTPException`, status codes |
| **Repository** (`app/repositories/`) | persistence queries | ORM models | business decisions, HTTP, `commit()` |

Read the "never contains" column as tripwires: any one of those appearing in the wrong layer recreates one of the three failures above.

---

## Repository: queries in, ORM objects out

```python
# app/repositories/link.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Link


class LinkRepository:
    """Persistence only. No business decisions, no HTTP, no commit."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_slug(self, slug: str) -> Link | None:
        return await self.db.scalar(select(Link).where(Link.slug == slug))

    async def list_recent(self, limit: int = 50) -> list[Link]:
        result = await self.db.scalars(
            select(Link).order_by(Link.created_at.desc()).limit(limit)
        )
        return list(result)

    async def add(self, link: Link) -> Link:
        self.db.add(link)
        await self.db.flush()   # sends INSERT, populates link.id — no commit (lesson 06-2)
        return link
```

Notice what's *absent*: `get_by_slug` doesn't check expiry, `add` doesn't retry collisions. Why that restraint matters: a rule buried in a `WHERE` clause is invisible. If the repository silently filters out expired links, then the admin endpoint that must *show* expired links either can't use the repo or grows a second, contradictory method — and when the expiry rule changes, you're hunting through SQL to find where it's encoded. Repositories answer "what's in the database", never "what should we do about it".

The payoff you get in exchange: when Postgres query shape changes — you add an index hint, switch to a CTE, denormalize a column — only this file changes. Business rules don't know and don't care.

---

## Service: rules, orchestration, domain exceptions

```python
# app/services/link.py — note: zero fastapi imports
import secrets
from datetime import UTC, datetime, timedelta

from app.models import Link
from app.repositories.link import LinkRepository


class LinkNotFoundError(Exception): ...
class SlugTakenError(Exception): ...
class LinkExpiredError(Exception): ...


class LinkService:
    def __init__(self, repo: LinkRepository) -> None:
        self.repo = repo

    async def create(
        self, target_url: str, slug: str | None = None, ttl_days: int | None = None
    ) -> Link:
        if slug is not None:                       # caller chose it: taken means taken
            if await self.repo.get_by_slug(slug):
                raise SlugTakenError(slug)
        else:                                      # we generate: retry on collision
            for _ in range(3):
                slug = secrets.token_urlsafe(4)
                if await self.repo.get_by_slug(slug) is None:
                    break
            else:
                raise SlugTakenError("could not generate a free slug")
        expires = datetime.now(UTC) + timedelta(days=ttl_days) if ttl_days else None
        return await self.repo.add(Link(slug=slug, target_url=target_url, expires_at=expires))

    async def resolve(self, slug: str) -> Link:
        link = await self.repo.get_by_slug(slug)
        if link is None:
            raise LinkNotFoundError(slug)
        if link.expires_at is not None and link.expires_at < datetime.now(UTC):
            raise LinkExpiredError(slug)
        return link
```

Why domain exceptions instead of `HTTPException`? Because the moment a service raises `HTTPException(409)`, it has decided it will only ever be called from a web request. The Arq job that calls `service.create()` would crash with an HTTP error it has no way to serve; the unit test must import FastAPI to assert on failures. `SlugTakenError` states *what happened* in domain terms — each caller decides what that means (a 409 for REST, a retry for the job, a log line for the CLI). Lesson 06-2 shows how these become HTTP responses in one place.

This service serves REST today and, unchanged, an Arq worker or a `python -m` CLI tomorrow — that's the reuse boundary working.

---

## Router: parse → call → shape

The DTOs first — routers speak Pydantic, not ORM:

```python
# app/schemas/link.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class LinkCreate(BaseModel):
    target_url: HttpUrl
    slug: str | None = None
    ttl_days: int | None = None


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)   # build from ORM attributes

    slug: str
    target_url: str
    created_at: datetime
    expires_at: datetime | None
```

Then the handler shrinks to its actual job:

```python
# app/api/v1/links.py
from fastapi import APIRouter, status

from app.api.deps import LinkServiceDep
from app.schemas.link import LinkCreate, LinkOut

router = APIRouter(prefix="/links", tags=["links"])


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(body: LinkCreate, service: LinkServiceDep) -> LinkOut:
    link = await service.create(
        str(body.target_url), slug=body.slug, ttl_days=body.ttl_days
    )
    return LinkOut.model_validate(link)
```

Five lines of body. Input validation (`HttpUrl`, field types) is Pydantic's job at the edge; the rule ("slugs must be unique") is the service's; the query is the repo's. There is almost nothing left in the handler *to* test — a couple of thin integration tests covering status codes and JSON shape suffice, while the rules get fast unit tests below.

---

## The DTO boundary — why ORM objects must not leak out

`return link` (the raw ORM object) from a handler *works*… until it doesn't:

- **Your table becomes your API contract.** Add an internal column — `owner_ip`, `hashed_password` on a user — and it appears in JSON responses the moment the migration lands. Rename a column and every client breaks, with no failing test, because nothing declared the response shape.
- **Async lazy-loading blows up at serialization time.** Serializing an ORM object with an unloaded relationship triggers a lazy load *outside* the session context — under async SQLAlchemy that's the infamous `MissingGreenlet` error, thrown from deep inside the serializer at runtime.

So: routers speak Pydantic schemas, repositories speak ORM models, and the translation happens exactly once, at the edge — `LinkOut.model_validate(link)` with `from_attributes=True`. The schema is a deliberate, explicit list of what the outside world may see; the table can now evolve freely behind it.

---

## Wiring it with DI

Dependencies compose: service needs a repo, repo needs a session. Declare the chain once:

```python
# app/api/deps.py
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.link import LinkRepository
from app.services.link import LinkService

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_link_service(db: DbSession) -> LinkService:
    return LinkService(LinkRepository(db))


LinkServiceDep = Annotated[LinkService, Depends(get_link_service)]
```

Every handler that declares `service: LinkServiceDep` gets a service wired to a repo wired to *that request's* session. No DI container library, no registry — `Depends` plus plain constructors is the whole mechanism. Note there's also no `LinkServiceInterface` or `AbstractRepository`: an interface with exactly one implementation is indirection with no payoff. Python classes are already substitutable — as the next section proves.

---

## The payoff: testing rules in milliseconds

Because `LinkService` depends on "something with `get_by_slug` and `add`", a fake in ten lines replaces the entire database:

```python
# tests/test_link_service.py — no TestClient, no DB, no fastapi import
import pytest

from app.services.link import LinkService, SlugTakenError


class FakeRepo:
    def __init__(self) -> None:
        self.by_slug = {}

    async def get_by_slug(self, slug):
        return self.by_slug.get(slug)

    async def add(self, link):
        self.by_slug[link.slug] = link
        return link


async def test_chosen_slug_collision_raises() -> None:
    service = LinkService(FakeRepo())
    await service.create("https://a.example", slug="docs")
    with pytest.raises(SlugTakenError):
        await service.create("https://b.example", slug="docs")
```

This test runs in under a millisecond and fails for exactly one reason: the rule broke. Compare with the fat-handler version, where the same assertion needed an app, a client, and a seeded database. Repositories, meanwhile, get a handful of tests against a real DB fixture (their only job is talking to it), and handlers barely need tests at all. That distribution — many fast rule tests, few slow plumbing tests — is the practical definition of a testable architecture.

---

## When NOT to add a layer

Layers are load-bearing, not ritual. Every boundary above earns its place by preventing a named failure — and where there's no failure to prevent, the boundary is pure overhead:

- **A 5-endpoint CRUD app with no rules?** Router + repository is enough. A service whose every method is `return await self.repo.x(...)` is a pass-through — delete it, and add the service *when the first real rule appears* (linkbox earned its service at "collision retry", not before).
- **No generic `Repository[T]` base class.** Two concrete repos with a similar shape are fine; a generic base with `get`, `list`, `create`, `update`, `delete` forces every model into CRUD whether it fits or not, and you'll fight it the first time a query needs a join.
- **No interfaces with one implementation.** You saw `FakeRepo` substitute for `LinkRepository` without any `Protocol` or ABC. Add a `Protocol` only if a type checker complaint actually bites you.

The test is always the same: *what concrete failure does this boundary prevent?* If you can't name one, you're building ceremony.

---

## Recap & next

- ✅ **Router:** HTTP in/out only — parse with a schema, call the service, shape with a schema.
- ✅ **Service:** business rules and orchestration; raises domain exceptions; zero `fastapi` imports — so it's unit-testable and reusable from jobs/CLI.
- ✅ **Repository:** queries only, ORM objects out, no business decisions — so query changes don't touch rules.
- ✅ **DTO boundary:** Pydantic at the edge (`from_attributes=True`); leaking ORM objects couples your API contract to your table shape.
- ✅ **Anti-ceremony:** no pass-through services, no `Repository[T]`, no one-implementation interfaces.
- ✅ Self-check: your teammate adds `if link.expires_at < now(): return None` inside `LinkRepository.get_by_slug`. Which two concrete failures does that create? *(Hint: the admin listing, and where did the 410 go?)*

→ Next: **[06-2 · Transactions & the unit of work](02_transactions_unit_of_work.md)**

## Exercises

1. Add "list only active links" to linkbox: `GET /links?active=true` returns links that haven't expired. Decide which piece of that feature belongs in which layer before writing code.

<details>
<summary>Solution</summary>

- **Repository:** the query shape — `async def list_unexpired(self, now: datetime) -> list[Link]` with `where(or_(Link.expires_at.is_(None), Link.expires_at > now))`. It takes `now` as a parameter: the repo runs the filter but doesn't decide what "now" or "active" means.
- **Service:** the decision — `list_links(active_only: bool)` supplies `datetime.now(UTC)` and picks `list_unexpired` vs `list_recent`. If "active" later means "not expired *and* not disabled", only this method changes.
- **Router:** `active: bool = False` query param, call service, `list[LinkOut]` response model.
</details>

2. Using `FakeRepo` from this lesson, write a unit test proving the *generated*-slug path retries on collision: pre-seed the fake so the first generated slug always collides, and assert `create` still succeeds. (Hint: make `get_by_slug` return a sentinel for the first call only, or pre-fill `by_slug` after monkeypatching `secrets.token_urlsafe` to return a known sequence.)

<details>
<summary>Solution</summary>

```python
async def test_generated_slug_retries_on_collision(monkeypatch) -> None:
    slugs = iter(["taken", "taken", "free"])
    monkeypatch.setattr("app.services.link.secrets.token_urlsafe", lambda n: next(slugs))

    repo = FakeRepo()
    repo.by_slug["taken"] = object()          # first two generations collide

    link = await LinkService(repo).create("https://a.example")
    assert link.slug == "free"                # third attempt won
```

Monkeypatching `secrets.token_urlsafe` *where the service looks it up* makes the retry loop deterministic. Still no DB, still no HTTP.
</details>

3. Break the DTO boundary on purpose: change the handler to `return link` with no `response_model`, then add a new column to `Link` (say `owner_ip: Mapped[str | None]`) and hit the endpoint. What does the response contain, and which test would have caught it?

<details>
<summary>Solution</summary>

The response now includes `owner_ip` — an internal column shipped to every client, with no code review line that said so (the migration did it). No test catches it, because nothing declares the expected shape. With `response_model=LinkOut`, the schema is an allowlist: new columns stay private until you *choose* to expose them, and a snapshot/contract test on the JSON keys would fail loudly if the shape drifted.
</details>
