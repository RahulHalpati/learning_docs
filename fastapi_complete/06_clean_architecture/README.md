# Section 06 · Clean architecture: routers → services → repositories

> **Prerequisites:** [05 · Async database: SQLAlchemy 2.0 + Alembic](../05_async_database_sqlalchemy_alembic/README.md) · **Time:** ~4 h

So far, your route handlers do everything: parse the request, run queries, apply rules, commit, shape the response. That works at 5 endpoints and collapses at 50 — handlers become untestable, logic gets copy-pasted, and commits hide in the middle of business rules. This section splits the app into three layers with sharp contracts — **routers** (HTTP only), **services** (business rules only), **repositories** (queries only) — and puts the transaction where it belongs: in one place.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 06-1 | [Layers & boundaries](01_layers_and_boundaries.md) | What exactly does each layer own — and what concrete failure appears when it owns more? |
| 06-2 | [Transactions & the unit of work](02_transactions_unit_of_work.md) | Who commits, when — and how do multi-step writes stay atomic? |

## Mini-project

**Linkbox, layered** — refactor the DB-backed linkbox app from Section 05 into three layers. Same endpoints, same behavior, new shape:

- `app/repositories/link.py` — `LinkRepository`: queries only (`select`, `flush`), takes and returns ORM `Link` objects, knows nothing about HTTP or business rules.
- `app/services/link.py` — `LinkService`: slug generation, collision retry, expiry logic. Raises domain exceptions (`SlugTakenError`, `LinkNotFoundError`, `LinkExpiredError`). Zero `fastapi` imports.
- `app/api/v1/links.py` — thin routers: parse (Pydantic schema in) → call service → shape (schema out). Domain exceptions become HTTP responses in **one** app-level exception handler, not in each route.

Requirements checklist:

- [ ] All Section 05 endpoints still work: create link (custom or generated slug), resolve/redirect by slug, list links.
- [ ] `grep -rn "fastapi" app/services app/repositories` returns **nothing**.
- [ ] `grep -rn "commit()" app` shows exactly **one** hit: the `get_db` dependency. Repositories and services use `flush()` only.
- [ ] Repository methods contain no business decisions — no "is it expired?", no retry loops, no status codes. Queries in, ORM objects (or `None`) out.
- [ ] Every business rule (slug generation, collision retry, expiry check) lives in `LinkService` and is exercised by at least one **unit test with a fake repository** — no `TestClient`, no database. This proves the service is importable and callable without FastAPI.
- [ ] `SlugTakenError` → 409, `LinkNotFoundError` → 404, `LinkExpiredError` → 410, mapped in one `@app.exception_handler` — no `HTTPException` below the router layer.
- [ ] Routers are ≤ ~10 lines each and contain no `select()` and no `try/except`.

## Test task (gate)

A code-review + refactor challenge. Below is a real-world fat handler — the kind you will inherit at a job. **Part 1:** review it — list every boundary violation you can find (there are at least eight). **Part 2:** refactor it into the three layers.

```python
# app/api/v1/users.py — the handler you're given. Refactor it.
import re
import secrets
import smtplib
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Project, User

router = APIRouter()
password_hash = PasswordHash.recommended()


class RegisterIn(BaseModel):
    email: str
    password: str
    display_name: str | None = None


@router.post("/register", status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    # ---- validation, inline ----
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", body.email):
        raise HTTPException(status_code=422, detail="invalid email")
    if len(body.password) < 10:
        raise HTTPException(status_code=422, detail="password too short")
    if body.display_name is not None and len(body.display_name) > 50:
        raise HTTPException(status_code=422, detail="display name too long")

    # ---- uniqueness check, direct query ----
    existing = await db.scalar(select(User).where(User.email == body.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=409, detail="email already registered")

    # ---- create the user ----
    user = User(
        email=body.email.lower(),
        hashed_password=password_hash.hash(body.password),
        display_name=body.display_name or body.email.split("@")[0],
    )
    db.add(user)
    await db.commit()  # commit #1 — the user is now permanent, no matter what
    await db.refresh(user)

    # ---- create the default project ----
    slug = f"{user.display_name.lower().replace(' ', '-')}-default"
    clash = await db.scalar(select(Project).where(Project.slug == slug))
    if clash is not None:
        slug = f"{slug}-{secrets.token_hex(3)}"
        clash = await db.scalar(select(Project).where(Project.slug == slug))
        if clash is not None:
            # HTTP raised from the middle of business logic
            raise HTTPException(status_code=500, detail="could not allocate slug")
    project = Project(name="Default project", slug=slug, owner_id=user.id)
    db.add(project)
    await db.commit()  # commit #2 — hope nothing failed between #1 and here

    # ---- welcome email, inline SMTP ----
    msg = EmailMessage()
    msg["From"] = "hello@example.com"
    msg["To"] = user.email
    msg["Subject"] = "Welcome!"
    msg.set_content(f"Hi {user.display_name}, your project '{project.name}' is ready.")
    try:
        with smtplib.SMTP("localhost", 25, timeout=5) as smtp:  # blocking call in async def
            smtp.send_message(msg)
    except OSError:
        raise HTTPException(status_code=500, detail="could not send welcome email")

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "default_project": {"id": project.id, "slug": project.slug},
    }
```

**Passing means, exactly:**

- The refactored handler is **≤ ~15 lines**: parse → call one service method → shape the response with a Pydantic schema.
- The service module has **zero `fastapi` imports** — verify with `grep -n "fastapi" app/services/*.py`.
- The repositories contain **zero business rules** — no validation, no slug retry, no email; only queries and `flush()`.
- There is **one commit point** — the `get_db` dependency. If project creation fails, no user row exists afterwards (write the test that proves it).
- Domain errors (`EmailTakenError`, `SlugAllocationError`, …) are raised by the service and mapped to 409/500 in **one** app-level exception handler.
- The email send is behind a **dependency** (e.g. an `EmailSender` with a `send()` method, injected into the handler or service) so a test can swap in a fake — your test suite must never open an SMTP connection. Bonus honesty point: notice the email is sent *before* the commit in your refactor's request lifecycle, and say in one sentence why "send after commit" (or a queued job — Section 10) is the correct ordering.

Miss any of these and it's not a pass — redo it. This gate exists because Section 07 builds auth *as a service*, and that only works if you can hold these boundaries without thinking.

## What you'll be able to do after this section

- State the exact contract of router, service, and repository — and spot a violation in code review within seconds.
- Unit-test business rules with a fake repository: no HTTP client, no database, millisecond tests.
- Keep multi-step writes atomic with one request-scoped transaction — `flush()` in layers, a single `commit()` in `get_db`.
- Map domain exceptions to HTTP status codes in one place, keeping `HTTPException` out of business logic.
- Say **no** to ceremony: recognize when a service layer, a generic base class, or a unit-of-work class is dead weight.

→ Start: **[06-1 · Layers & boundaries](01_layers_and_boundaries.md)**
