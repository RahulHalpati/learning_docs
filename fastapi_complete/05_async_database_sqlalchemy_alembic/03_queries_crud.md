# 05-3 · Queries & CRUD

> **Level:** Intermediate · **Prerequisites:** [05-2 · Models & relationships](02_models_and_relationships.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (SQLAlchemy 2.0 · asyncpg · Alembic · PostgreSQL 16)

## Why this matters

Every request your service handles ends in one of these operations. The 2.0 query style (`select()` + `scalars()`) is one consistent, typed API for all of it — but knowing the *right* operation matters more than syntax: offset pagination that dies at page 10 000, a fetch-modify loop where one `UPDATE` would do, or a get-then-insert race that an upsert eliminates — these are the differences reviewers (and incidents) notice.

---

## Reading: `select()` + `scalars()`

The 2.0 pattern: build a `select()` statement, execute it, pull typed objects out. (Legacy `session.query()` is dead — you'll see it in old tutorials; don't write it.)

```python
from sqlalchemy import select

# Many rows → scalars().all()
result = await db.scalars(
    select(Link)
    .where(Link.is_active == True)              # noqa: E712 — SQL expression, not Python bool
    .order_by(Link.created_at.desc())
)
links = result.all()                            # list[Link]

# One row or None → scalar_one_or_none()
result = await db.execute(select(Link).where(Link.slug == slug))
link = result.scalar_one_or_none()              # Link | None
if link is None:
    raise HTTPException(status_code=404, detail="Link not found")
```

- **`scalars()`** unwraps each row to the entity itself — without it you get `Row` tuples (`(Link,)`), which you only want when selecting multiple things.
- **`scalar_one_or_none()`** encodes "at most one": returns the object, `None` if missing, and *raises* if the query matched multiple rows — a broken uniqueness assumption should blow up, not silently return the first match.
- `.where()` clauses chain (they AND together); `.order_by()` takes `.asc()` / `.desc()`.

---

## Pagination: offset first, keyset at scale

**Limit/offset** — trivial to implement, fine for admin screens and small tables:

```python
@router.get("/links")
async def list_links(db: DbSession, page: int = 1, size: int = 20):
    result = await db.scalars(
        select(Link).order_by(Link.id.desc()).offset((page - 1) * size).limit(size)
    )
    return result.all()
```

The catch: `OFFSET 100000` makes Postgres **read and discard 100 000 rows** to reach your 20 — page latency grows linearly with page number. Worse, rows inserted between page loads shift everything, so users see duplicates or gaps.

**Keyset (cursor) pagination** — instead of "skip N rows", ask for "rows after the last one I saw", using the ordered column itself:

```python
@router.get("/links")
async def list_links(db: DbSession, cursor: int | None = None, size: int = 20):
    stmt = select(Link).order_by(Link.id.desc()).limit(size)
    if cursor is not None:
        stmt = stmt.where(Link.id < cursor)     # continue after the last-seen id
    links = (await db.scalars(stmt)).all()
    next_cursor = links[-1].id if len(links) == size else None
    return {"items": links, "next_cursor": next_cursor}
```

`WHERE id < cursor` is an index seek — **constant time on page 1 and page 10 000**, and immune to concurrent inserts. The trade-off: no "jump to page 47", and the cursor column must be unique-and-ordered (an id, or `(created_at, id)` as a composite). Public APIs (Stripe, GitHub, Slack) are keyset for exactly these reasons — use offset for small internal lists, keyset for anything user-facing that grows.

---

## Creating: `add()` + `flush()` — not `commit()`

```python
async def create_link(db: AsyncSession, data: LinkCreate) -> Link:
    link = Link(slug=data.slug, url=str(data.url))
    db.add(link)            # registered with the session — no SQL yet
    await db.flush()        # INSERT sent, link.id now populated
    return link             # commit happens in get_db, after the request succeeds
```

**Flush vs commit** — keep these straight:

- **`flush()`** sends pending SQL to the database *inside the open transaction*. You get generated values back (`link.id`, server defaults) and later statements in the same request can see the row. Nothing is permanent yet.
- **`commit()`** ends the transaction and makes everything durable. Per 05-1, that happens **once**, in `get_db`, after the endpoint returns — business code flushes when it needs ids, and never commits.

---

## Updating: fetch-modify vs `update()` statement

**Fetch-modify** — the default for single entities in request handlers:

```python
result = await db.execute(select(Link).where(Link.slug == slug))
link = result.scalar_one_or_none()
if link is None:
    raise HTTPException(status_code=404)
link.url = str(data.url)        # session tracks the change
await db.flush()                # UPDATE emitted; commit in get_db
```

Use it when you're updating **one object you already need to load anyway** — for validation, permission checks, or returning it in the response. The change also runs Python-side logic (`onupdate=func.now()` on the mixin, event listeners).

**`update()` statement** — one SQL statement, no objects loaded:

```python
from sqlalchemy import update

await db.execute(
    update(Link)
    .where(Link.expires_at < func.now())
    .values(is_active=False)
)
```

Use it for **bulk changes**: deactivating 50 000 expired links via fetch-modify means 50 000 SELECT-load-UPDATE cycles; the statement is one round trip and lets Postgres do the work. The trade-off: it bypasses the ORM — no Python-side `onupdate`, no cascades, no in-session objects updated. Rule of thumb: *one row you're handling anyway → fetch-modify; many rows by criteria → `update()`*.

---

## Deleting

```python
from sqlalchemy import delete

# ORM delete — runs relationship cascades (delete-orphan from 05-2)
await db.delete(link)
await db.flush()

# Bulk delete — one statement, only FK-level ON DELETE applies
await db.execute(
    delete(ClickEvent).where(ClickEvent.clicked_at < cutoff)
)
```

Same split as updates: `db.delete(obj)` for an object in hand (honors ORM cascade rules), `delete()` statement for sweeping many rows (only the database's `ondelete` behavior applies — one more reason 05-2 set the FK cascade too).

---

## Upsert: PostgreSQL `ON CONFLICT`

"Insert, or update if it exists" done as *check-then-insert* is a **race**: two concurrent requests both see "not there", both insert, one crashes on the unique constraint. Postgres solves it atomically, and SQLAlchemy exposes it through the Postgres dialect:

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = (
    pg_insert(Link)
    .values(slug=data.slug, url=str(data.url))
    .on_conflict_do_update(
        index_elements=[Link.slug],           # the unique constraint to catch
        set_={"url": str(data.url)},          # what to change if it already exists
    )
    .returning(Link)
)
link = (await db.execute(stmt)).scalar_one()
```

One atomic statement — no race window, no retry loop. The sibling `on_conflict_do_nothing()` covers "insert if absent, otherwise ignore" (idempotent event ingestion, seed data). Note the import: this `insert` comes from `sqlalchemy.dialects.postgresql` — `ON CONFLICT` is a Postgres feature, not portable SQL.

---

## Counting correctly

```python
from sqlalchemy import func

total = await db.scalar(
    select(func.count()).select_from(Link).where(Link.is_active == True)  # noqa: E712
)
```

This emits `SELECT count(*) FROM links WHERE ...` — Postgres counts, one integer comes back. The tempting alternative, `len((await db.scalars(select(Link))).all())`, transfers **every row over the network and builds an ORM object for each** just to throw them away. Fine at 100 rows, a self-inflicted outage at 10 million.

---

## Recap & next

- ✅ Read with `select().where()` → `scalars().all()` for lists, `scalar_one_or_none()` for at-most-one.
- ✅ Offset pagination is O(page-number) and shifts under writes; **keyset** (`WHERE id < cursor`) is an index seek — use it for anything that grows.
- ✅ Create with `add()` + `flush()` (ids now, durability later); **commit stays in `get_db`**.
- ✅ One object in hand → fetch-modify / `db.delete()`; many rows by criteria → `update()` / `delete()` statements (ORM logic bypassed — know the trade).
- ✅ Upsert with `pg_insert(...).on_conflict_do_update()` — atomic, race-free. Count with `select(func.count())`, never `len(all())`.
- ✅ Self-check: why does check-then-insert race even though each request runs in its own transaction?

→ Next: **[05-4 · Migrations with Alembic](04_alembic_migrations.md)**

## Exercises

1. Convert your linkbox `GET /links` endpoint to keyset pagination returning `{"items": [...], "next_cursor": ...}`. What does `next_cursor = None` signal, and why is checking `len(links) == size` the right way to detect it?

<details>
<summary>Solution</summary>

As in the keyset block above. `next_cursor = None` signals the last page. A short page (`len(links) < size`) proves the table ran out of rows past the cursor, so there's nothing to continue from. (Edge case: a full page that's *exactly* the final page yields one extra empty request — acceptable, or fetch `size + 1` rows and use the extra as a lookahead.)
</details>

2. Track a per-link daily click counter in a `click_stats(link_id, day, count)` table with a unique constraint on `(link_id, day)`. Write the one-statement upsert that increments it.

<details>
<summary>Solution</summary>

```python
stmt = (
    pg_insert(ClickStat)
    .values(link_id=link_id, day=today, count=1)
    .on_conflict_do_update(
        index_elements=[ClickStat.link_id, ClickStat.day],
        set_={"count": ClickStat.count + 1},
    )
)
await db.execute(stmt)
```

`set_` can reference the existing column (`ClickStat.count + 1`), making the increment atomic in the database — concurrent clicks can't lose updates the way read-increment-write would.
</details>

3. A cleanup job deactivates expired links with fetch-modify: load all expired links, set `is_active = False` on each, flush. Rewrite it as a single statement, then name one thing the original did that your rewrite doesn't.

<details>
<summary>Solution</summary>

`await db.execute(update(Link).where(Link.expires_at < func.now()).values(is_active=False))`. What's lost: Python-side per-object behavior — the mixin's `onupdate=func.now()` for `updated_at` doesn't fire (add `updated_at=func.now()` to `.values()` to compensate), and any ORM event listeners or in-memory objects are bypassed. For 50 000 rows, that trade is worth it; just make it deliberately.
</details>
