# 02-1 · SQLAlchemy models

> **Level:** Intermediate · **Prerequisites:** [01-1 · Project layout](../01_foundations_and_structure/01_project_layout.md)
> **Time:** 45 min · **Verified:** 2026-07-27 (SQLAlchemy 2.0.51)

## Why this matters

Models are your database tables as Python classes. SQLAlchemy 2.0's typed `Mapped[...]` style makes them clear, autocomplete-friendly, and type-checkable — a big upgrade over the old `Column()` style. Get the models and their relationships right and the rest of the data layer follows.

---

## The declarative base + a mixin

Every model shares a base and (usually) timestamp columns — factor those out once:

```python
# app/db/base.py
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """All models inherit from this."""

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(),
                                                 onupdate=func.now())
```

`server_default=func.now()` lets the **database** set the timestamp; `onupdate` bumps `updated_at` on every change.

---

## A model with typed columns

```python
# app/models/user.py
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin
from app.models.enums import Role

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(default=Role.member)      # a Python Enum column
    is_active: Mapped[bool] = mapped_column(default=True)

    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan")
```

- **`Mapped[int]`** vs `Mapped[int | None]` — the type annotation controls `NOT NULL`. Non-optional = required.
- **`unique=True, index=True`** on email — enforce uniqueness and make lookups fast.
- **`role: Mapped[Role]`** — a Python `Enum` stored as its value; type-safe in code, a string in the DB.

> **Tip — store the hash, never the password.** The column is `hashed_password`, populated by bcrypt (Section 04). A plaintext-password column is a breach waiting to happen.

---

## Relationships & foreign keys

A project belongs to a user; a task belongs to a project. Model both sides:

```python
# app/models/project.py (essentials)
class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    owner: Mapped["User"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project",
                                               cascade="all, delete-orphan")
```

- **`ForeignKey("users.id", ondelete="CASCADE")`** — delete a user, their projects go too (enforced by the DB).
- **`relationship(back_populates=...)`** — the two-way link so `project.owner` and `user.projects` both work.
- **`cascade="all, delete-orphan"`** — the ORM-side cascade for children removed from a collection.
- **Index the FK** (`owner_id`) — you'll filter by it constantly ("this user's projects").

The data model in one picture: `User 1—* Project 1—* Task`, plus an optional `Task.assignee_id → User`.

---

## Verify: the models create their tables

```python
from app.db.base import Base
import app.models          # register User, Project, Task
# await conn.run_sync(Base.metadata.create_all)
print(sorted(Base.metadata.tables))
```

**Output (real run):**
```
['projects', 'tasks', 'users']
```

`Base.metadata` now knows all three tables and their columns/indexes — which is exactly what Alembic reads to generate migrations ([02-3](03_migrations_alembic.md)).

> ⚠️ **Import your models somewhere that runs.** SQLAlchemy only knows a table exists once its class is imported. `app/models/__init__.py` imports all three, and anything needing the full metadata (Alembic, `create_all`) imports `app.models`. Forget this and Alembic will "helpfully" try to *drop* your unseen tables.

---

## Recap & next

- ✅ SQLAlchemy 2.0 models are typed `Mapped[...]` classes; the annotation controls nullability.
- ✅ Use `ForeignKey(..., ondelete=...)` + `relationship(back_populates=...)` for relations; index your FKs.
- ✅ A `TimestampMixin` + `DeclarativeBase` keep models DRY.
- ✅ **Import all models** so `Base.metadata` (and Alembic) see them.
- ✅ Self-check: why does the `User` store `hashed_password` and not `password`?

→ Next: **[02-2 · Engine & session](02_engine_and_session.md)**

## Exercises

1. Add a `due_date: Mapped[datetime | None]` column to `Task`. What does the `| None` change about the database column?

<details>
<summary>Solution</summary>

`Mapped[datetime | None]` makes the column **nullable** (`NULL` allowed) — tasks without a due date are valid. Drop the `| None` and the column becomes `NOT NULL`, requiring a value on every task. The annotation *is* the nullability.
</details>
