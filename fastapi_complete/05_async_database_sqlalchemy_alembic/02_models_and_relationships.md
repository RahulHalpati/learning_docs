# 05-2 · Models & relationships

> **Level:** Intermediate · **Prerequisites:** [05-1 · Async engine & sessions](01_async_engine_sessions.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (SQLAlchemy 2.0 · asyncpg · Alembic · PostgreSQL 16)

## Why this matters

Models are your schema *as code*: the single source of truth that Alembic diffs against, your IDE type-checks against, and every query is written against. SQLAlchemy 2.0's typed `Mapped[...]` style means `link.slug` autocompletes as `str` and `mypy` catches `link.slgu` before production does. And in an async app, *how relationships load* is not an optimization detail — it's the difference between a working endpoint and a `MissingGreenlet` crash.

---

## Base and a typed model

Every model inherits from one `DeclarativeBase` subclass — it collects all table metadata (Alembic reads it from here):

```python
# app/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

```python
# app/models/link.py
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(2000))
    note: Mapped[str | None]                          # `| None` → nullable column
    is_active: Mapped[bool] = mapped_column(default=True)
```

How the pieces map:

- **`Mapped[str]`** → `NOT NULL`; **`Mapped[str | None]`** → nullable. Nullability lives in the *type annotation*, so your Python types and your schema can't disagree.
- **`mapped_column(...)`** carries the column details: `String(50)` (length), `unique=True`, `index=True`, `primary_key=True`. When there's nothing to configure (like `note`), the annotation alone suffices.
- **`default=True`** is a *Python-side* default — applied by SQLAlchemy at insert. For defaults the **database** computes, use `server_default` (next section) — those also cover rows inserted by anything that isn't your app (psql, another service, a data migration).

---

## Timestamps done right: a reusable mixin

Every table wants `created_at`/`updated_at`. Write it once:

```python
# app/db/base.py (continued)
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

Then `class Link(TimestampMixin, Base): ...` — both columns appear on every table that mixes it in.

- **`DateTime(timezone=True)`** → Postgres `timestamptz`. Naive timestamps are a production landmine: the moment a server, a replica, or a developer laptop disagrees on timezone, your "when did this happen" data is silently wrong. Always `timezone=True`, always store UTC.
- **`server_default=func.now()`** → `DEFAULT now()` *in the DDL*. The database stamps the row, so the timestamp is correct no matter who inserts — your app, a migration backfill, or someone in psql.

---

## One-to-many: Link → ClickEvent

```python
# app/models/click_event.py
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClickEvent(Base):
    __tablename__ = "click_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey("links.id", ondelete="CASCADE"))
    referrer: Mapped[str | None] = mapped_column(String(500))
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    link: Mapped["Link"] = relationship(back_populates="clicks")
```

```python
# app/models/link.py — add to Link:
    clicks: Mapped[list["ClickEvent"]] = relationship(
        back_populates="link",
        cascade="all, delete-orphan",
    )
```

- **`ForeignKey("links.id")`** is the real constraint, on the *table*. The `relationship()` is the Python-side view of it — no FK, no relationship.
- **`Mapped[list["ClickEvent"]]`** on the "one" side, **`Mapped["Link"]`** on the "many" side — the annotation's shape tells SQLAlchemy the direction. **`back_populates`** wires the two ends so `link.clicks.append(ev)` and `ev.link = link` stay in sync in memory.
- **Cascades — choose deliberately.** `cascade="all, delete-orphan"` means: deleting a `Link` via the ORM deletes its clicks, and a click removed from `link.clicks` is deleted rather than orphaned. Right for *owned* children (click events mean nothing without their link). Wrong for shared references — you wouldn't cascade-delete a `User` when their `Team` is deleted. `ondelete="CASCADE"` on the FK is the same policy *in the database* — it covers deletes that bypass the ORM (bulk `DELETE` statements, psql). Set both when the child is truly owned.

---

## Many-to-many: Link ↔ Tag

Many-to-many needs an **association table** — plain Core `Table`, since it has no model class of its own (Core tables use `Column`; `mapped_column` is only for declarative classes):

```python
# app/models/tag.py
from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

link_tags = Table(
    "link_tags",
    Base.metadata,
    Column("link_id", ForeignKey("links.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    links: Mapped[list["Link"]] = relationship(
        secondary=link_tags, back_populates="tags"
    )
```

```python
# app/models/link.py — add to Link:
    tags: Mapped[list["Tag"]] = relationship(
        secondary=link_tags, back_populates="links"
    )
```

The composite primary key on `(link_id, tag_id)` doubles as a uniqueness guarantee — a link can't carry the same tag twice. Note: no delete cascade *through* a many-to-many — deleting a link removes its `link_tags` rows (FK cascade), never the tags themselves; they're shared.

---

## THE async pitfall: lazy loading raises `MissingGreenlet`

By default, relationships load **lazily**: `link.clicks` emits a `SELECT` at the moment you touch it. In sync SQLAlchemy that's merely a performance foot-gun (N+1 queries). In **async** SQLAlchemy it's a crash:

```python
result = await db.execute(select(Link).where(Link.slug == slug))
link = result.scalar_one_or_none()
return link.clicks    # 💥 MissingGreenlet
```

Why: async I/O can only happen at an `await`. Attribute access (`link.clicks`) is plain synchronous Python — there is nowhere to `await` the query it wants to run. SQLAlchemy's async layer runs your ORM code inside a greenlet that bridges to the event loop; a lazy load fired outside that bridge (in your endpoint's return path, in Pydantic serialization, after the session closed) has no way to reach the loop → `MissingGreenlet`.

**The rule: in async, load explicitly. Decide at query time what you need.**

```python
from sqlalchemy.orm import joinedload, selectinload

# Collections → selectinload: 2nd query with WHERE id IN (...)
stmt = select(Link).options(selectinload(Link.clicks)).where(Link.slug == slug)

# Many-to-one → joinedload: single query with a JOIN
stmt = select(ClickEvent).options(joinedload(ClickEvent.link)).limit(50)
```

When each:

- **`selectinload` for collections** (one-to-many, many-to-many). It runs one extra `SELECT ... WHERE link_id IN (...)`. A JOIN would instead duplicate the parent row once per child — 100 links × 1 000 clicks = 100 000 rows over the wire.
- **`joinedload` for many-to-one** (`ClickEvent.link`). The parent is a single row per child; a JOIN adds it for free in the same round trip — no second query needed.

> **Tip — make the crash impossible.** Add `lazy="raise"` to a relationship (or set it as the default) and any *implicit* lazy load raises immediately with a clear error in development, instead of `MissingGreenlet` surprising you in an obscure serialization path.

---

## Recap & next

- ✅ `class Base(DeclarativeBase)` + `Mapped[...]`/`mapped_column` — nullability from `| None`, constraints (`unique`, `index`) in the column.
- ✅ `default` = app-side; `server_default` = in the DDL, covers every writer. Timestamps: `DateTime(timezone=True)` + `func.now()`, packaged in a mixin.
- ✅ One-to-many: FK on the child, `Mapped[list[...]]` + `back_populates`; cascade only for *owned* children (ORM cascade + FK `ondelete`).
- ✅ Many-to-many: Core association `Table` + `relationship(secondary=...)`.
- ✅ **Async lazy loading crashes with `MissingGreenlet`** — load explicitly: collections → `selectinload`, many-to-one → `joinedload`.
- ✅ Self-check: why is `selectinload` the wrong choice for `ClickEvent.link`, and `joinedload` the wrong choice for `Link.clicks`?

→ Next: **[05-3 · Queries & CRUD](03_queries_crud.md)**

## Exercises

1. Define the `Tag` model and `link_tags` association table in your linkbox app, wire both `relationship()` ends, and confirm in psql (`\d link_tags`) that the composite primary key exists.

<details>
<summary>Solution</summary>

As in the many-to-many section above: `link_tags = Table(..., Column("link_id", ForeignKey("links.id", ondelete="CASCADE"), primary_key=True), Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True))`, then `tags: Mapped[list["Tag"]] = relationship(secondary=link_tags, back_populates="links")` on `Link` and the mirror on `Tag`. `\d link_tags` shows `PRIMARY KEY (link_id, tag_id)` — which is also why the same tag can't be attached to a link twice.
</details>

2. Write an endpoint that fetches a `Link` *without* any loader options and returns `{"clicks": len(link.clicks)}`. Observe the `MissingGreenlet` traceback, then fix it two ways: (a) a loader option, (b) not loading the relationship at all.

<details>
<summary>Solution</summary>

(a) `select(Link).options(selectinload(Link.clicks))` — the collection is loaded at query time, so `len(link.clicks)` is a plain in-memory operation. (b) Better for a *count*: don't load 10 000 rows to count them — `await db.scalar(select(func.count()).select_from(ClickEvent).where(ClickEvent.link_id == link.id))` (details in 05-3). The fix isn't always "add a loader option"; sometimes it's "you never needed the objects."
</details>

3. Your `TimestampMixin` uses `server_default=func.now()`. A teammate proposes `default=datetime.now` instead. Name two concrete ways that version produces wrong data.

<details>
<summary>Solution</summary>

(1) `datetime.now()` without a timezone is *naive* and uses the app server's local clock/zone — two app servers in different zones write incomparable timestamps (`datetime.now(timezone.utc)` would fix that half). (2) It only fires for inserts made through the SQLAlchemy app — a backfill in a data migration, a psql insert, or another service writes `NULL` (or errors), because the default lives in Python, not in the table's DDL. `server_default` puts the rule where every writer hits it.
</details>
