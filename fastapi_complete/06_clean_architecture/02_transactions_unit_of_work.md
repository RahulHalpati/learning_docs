# 06-2 · Transactions & the unit of work

> **Level:** Intermediate · **Prerequisites:** [06-1 · Layers & boundaries](01_layers_and_boundaries.md)
> **Time:** ~40–50 min · **Verified:** 2026-08-07 (FastAPI 0.116 · SQLAlchemy 2.0 · Pydantic 2.11)

## Why this matters

Layers answer "where does the code live"; this lesson answers "who owns the transaction" — because a `commit()` in the wrong layer silently destroys atomicity. The failure isn't theoretical: a commit between two related writes means the first one survives when the second one fails, and you ship half-written state to production. The fix is one rule, enforced by structure: **the request commits, the layers only flush.**

---

## Who owns the transaction

You already built the owner in Section 05 — the `get_db` dependency:

```python
# app/db/session.py (from Section 05 — unchanged)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()      # the ONE commit: request succeeded
        except Exception:
            await session.rollback()    # anything raised → undo everything
            raise
```

Everything below the router shares that request-scoped session and follows one division of labor:

| Call | What it does | Who calls it |
|------|--------------|--------------|
| `session.flush()` | sends pending SQL (INSERTs get you generated ids), **transaction still open** | repositories |
| `session.commit()` | makes everything since request start permanent | `get_db`, nowhere else |
| `session.rollback()` | undoes everything since request start | `get_db`, nowhere else |

`flush()` is why repos can hand back a `Link` with its `id` populated without ending the transaction: the INSERT has been sent to the database, but it's still undoable until the request-level commit.

---

## The concrete failure scattered commits cause

Here's a registration service written by someone who commits "to be safe":

```python
# BROKEN — do not copy
class RegistrationService:
    async def register(self, email: str, password: str) -> User:
        user = User(email=email, hashed_password=self.hasher.hash(password))
        self.db.add(user)
        await self.db.commit()          # ← user is now PERMANENT

        project = Project(name="Default project", owner_id=user.id)
        self.db.add(project)
        await self.db.commit()          # ← if THIS raises (constraint, disk, deploy
        return user                     #    mid-request), the user still exists
```

Walk the failure: the second commit hits a constraint violation. The request 500s — but commit #1 already ran, so the user row is permanent. The user retries and gets **409 email already registered**. They now have an account with no project, every "list my projects" call breaks an invariant your code assumed ("every user has a default project"), and support gets a ticket nobody can reproduce. That is what "commit in the middle" costs.

The fixed version doesn't manage the transaction at all:

```python
# FIXED — the service orchestrates, the request commits
class RegistrationService:
    def __init__(self, users: UserRepository, projects: ProjectRepository) -> None:
        self.users = users          # both repos hold the SAME request session
        self.projects = projects

    async def register(self, email: str, password: str) -> User:
        if await self.users.get_by_email(email):
            raise EmailTakenError(email)
        user = await self.users.add(          # flush() inside → user.id exists,
            User(email=email, hashed_password=self.hasher.hash(password))
        )                                     # but nothing is permanent yet
        await self.projects.add(Project(name="Default project", owner_id=user.id))
        return user
        # get_db commits after the handler returns: both rows or neither
```

If the project insert fails now, the exception propagates up through `get_db`, the `except` branch rolls back, and the user INSERT — already flushed, never committed — evaporates. Retry works. No half-state. Nothing in the service even mentions transactions; the structure guarantees the outcome.

---

## This is the unit of work — and you already have one

The pattern has a name: **unit of work** — collect all changes belonging to one business operation, then commit or roll back *as a unit*. Two things are worth knowing about it:

1. **SQLAlchemy's `Session` literally is one.** Tracking added/dirty/deleted objects, flushing them inside one transaction, committing or rolling back atomically — that's the session's job description. It's the textbook pattern, already implemented and battle-tested.
2. **Your plumbing already scopes it correctly.** `async_sessionmaker` creates one session per request; `get_db` opens it, hands the *same instance* to every repository in the dependency chain, and closes the unit with one commit/rollback. `RegistrationService` above spans two repositories and two tables in one atomic operation with zero extra code — because both repos share the request's session.

Which leads to a warning: you will find tutorials insisting on a `UnitOfWork` class — `async with uow:`, a repository registry, `uow.commit()`, an abstract base for testability. For a FastAPI service that's ceremony: it re-implements what `get_db` already does, adds a layer every developer must learn, and its main advertised benefit (swapping persistence wholesale) is a speculative need. **When NOT to add this layer:** if "one session per request, one commit in the dependency" already gives you atomic multi-repo operations — and it does — a UoW wrapper class adds surface area, not safety. Build it only when you genuinely have multiple transaction scopes per request to coordinate, which is rare enough that you'll know.

---

## The same unit of work outside FastAPI

Owning the transaction at the *entry point* (not in the service) is also what makes services reusable. A worker or CLI just brings its own transaction scope:

```python
# app/worker.py — same service, no FastAPI anywhere
from app.db.session import SessionLocal
from app.repositories.link import LinkRepository
from app.services.link import LinkService


async def purge_expired_links(ctx: dict) -> int:      # an Arq job
    async with SessionLocal() as session:
        async with session.begin():                   # commit on success, rollback on error
            service = LinkService(LinkRepository(session))
            return await service.purge_expired()
```

`session.begin()` plays the role `get_db` plays for requests. The service is identical in both worlds because it never claimed transaction ownership — the caller that opens the unit of work closes it.

---

## Domain exceptions → HTTP, in one place

Lesson 06-1 left a thread hanging: services raise `SlugTakenError`, but clients need a 409. The mapping lives in app-level exception handlers — the only place domain errors and HTTP meet:

```python
# app/services/errors.py — shared base, still zero fastapi imports
class DomainError(Exception):
    """Base for all business-rule violations."""
```

```python
# app/api/errors.py — the ONE place domain meets HTTP
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.errors import DomainError
from app.services.link import LinkExpiredError, LinkNotFoundError, SlugTakenError

STATUS: dict[type[DomainError], int] = {
    LinkNotFoundError: 404,
    SlugTakenError: 409,
    LinkExpiredError: 410,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)                    # catches all subclasses
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=STATUS.get(type(exc), 400),
            content={"detail": str(exc)},
        )
```

(Make the domain exceptions from 06-1 subclass `DomainError`; the handler matches subclasses via the exception's MRO, so one registration covers them all. Call `register_error_handlers(app)` in your app factory.)

Why this beats `try/except SlugTakenError: raise HTTPException(409)` in every route:

- **The mapping is a policy, stated once.** "Slug conflicts are 409" is written in exactly one file. When ten endpoints can raise it, you don't maintain ten translations that drift ("this one returns 400, why?").
- **Routes stay thin.** The handler from 06-1 has no `try/except` — it can't forget one.
- **Order of operations is safe.** When the service raises, the exception first passes through `get_db`'s `yield`, triggering the **rollback** — then FastAPI's handler shapes the response. A failed business rule never leaves flushed writes behind *and* never returns a raw 500.

The rule stands: `HTTPException` above the service line only — and with central handlers, mostly not even there.

---

## Savepoints: the rare explicit transaction

One legitimate case for touching transaction machinery below `get_db`: you want to *attempt* a write, tolerate its failure, and keep the surrounding transaction alive. Example: race-proof slug insertion — two concurrent requests can both pass a `get_by_slug` check, and only the unique constraint catches the second one at INSERT time:

```python
# app/repositories/link.py — race-safe insert using a SAVEPOINT
from sqlalchemy.exc import IntegrityError

async def add_racesafe(self, link: Link, reslug: Callable[[], str]) -> Link:
    for _ in range(3):
        try:
            async with self.db.begin_nested():   # SAVEPOINT, not a real commit
                self.db.add(link)
                await self.db.flush()            # INSERT runs → may hit UNIQUE
            return link
        except IntegrityError:
            link.slug = reslug()                 # savepoint rolled back; the outer
    raise SlugCollisionError(link.slug)          # request transaction is still fine
```

Without `begin_nested()`, the `IntegrityError` poisons the whole session — every later statement in the request fails with *"transaction has been rolled back"*. The savepoint confines the damage to the failed INSERT, so the retry (and the request's other writes) proceed, and `get_db` still owns the final commit.

That's the whole use case: **partial-failure tolerance inside one request**. If you're not catching a specific expected error to retry or degrade gracefully, you don't need savepoints — most services never write `begin_nested()` once.

---

## Recap & next

- ✅ **One commit per request, in `get_db`.** Services and repositories `flush()` to get ids; they never commit or roll back.
- ✅ Scattered commits break atomicity — the user-without-a-project failure is the canonical half-written state.
- ✅ Multi-repo operations are atomic *for free* because every repo shares the request session — that **is** the unit-of-work pattern; `Session` implements it, `get_db` scopes it. Don't build a UoW class to wrap a UoW.
- ✅ Domain exceptions map to HTTP in one `@app.exception_handler(DomainError)`; rollback happens first, then the response is shaped.
- ✅ `begin_nested()` (savepoints) only for tolerating an expected failure mid-transaction, e.g. unique-constraint retry.
- ✅ Self-check: a teammate adds `await self.db.commit()` at the end of `UserRepository.add` "so callers don't forget". Explain the exact failure scenario this creates in `RegistrationService.register`.

→ Next: **[Section 07 · Security & auth](../07_security_auth/README.md)**

## Exercises

1. Break atomicity on purpose in your linkbox refactor: put a `commit()` inside `LinkRepository.add`, then make the service raise *after* calling it (e.g. a fake rule `raise SlugTakenError` post-add). Hit the endpoint, then query the table. What's in it, and why didn't `get_db`'s rollback save you?

<details>
<summary>Solution</summary>

The link row is in the table. `get_db` did call `rollback()` when the exception passed through the `yield` — but rollback only undoes the *current* transaction, and the repo's `commit()` had already ended it (the session began a fresh transaction on the next statement). Once committed, data is permanent; no outer code can retract it. That's why the checklist item is "grep for `commit()` — exactly one hit": the guarantee is structural, not a convention people remember under deadline.
</details>

2. Write the test that the section gate demands: calling `RegistrationService.register` where project creation fails must leave **no** user row. Use your real DB test fixture (from Section 05), a `ProjectRepository` stub that raises, and assert the users table is empty afterwards.

<details>
<summary>Solution</summary>

```python
async def test_failed_project_rolls_back_user(db_session) -> None:
    class ExplodingProjects:
        async def add(self, project):
            raise RuntimeError("boom")

    service = RegistrationService(UserRepository(db_session), ExplodingProjects())

    with pytest.raises(RuntimeError):
        await service.register("a@example.com", "s3cret-password")
    await db_session.rollback()               # what get_db would do

    count = await db_session.scalar(select(func.count()).select_from(User))
    assert count == 0                         # flushed, never committed → gone
```

The user INSERT was flushed (it got an id) but the rollback erased it. If your repo committed internally, this test fails with `count == 1` — which is exactly the bug it guards against.
</details>

3. Your linkbox `resolve` endpoint should return `410 Gone` with body `{"detail": "link expired", "expired_at": "..."}` — the expiry timestamp, not just a message. Extend the exception + handler to carry structured data without letting HTTP leak into the service.

<details>
<summary>Solution</summary>

Give the domain exception data, not HTTP:

```python
# app/services/link.py
class LinkExpiredError(DomainError):
    def __init__(self, slug: str, expired_at: datetime) -> None:
        super().__init__(f"link '{slug}' expired")
        self.expired_at = expired_at
```

Then branch in the *handler*, where HTTP lives:

```python
@app.exception_handler(LinkExpiredError)
async def link_expired(request: Request, exc: LinkExpiredError) -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={"detail": str(exc), "expired_at": exc.expired_at.isoformat()},
    )
```

A specific handler registered alongside the generic `DomainError` one wins for this subclass (most-specific match via MRO). The service still knows nothing about status codes or JSON — it just reports facts.
</details>
