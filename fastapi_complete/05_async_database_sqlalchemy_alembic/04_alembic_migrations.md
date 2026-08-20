# 05-4 · Migrations with Alembic

> **Level:** Intermediate · **Prerequisites:** [05-3 · Queries & CRUD](03_queries_crud.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (SQLAlchemy 2.0 · asyncpg · Alembic · PostgreSQL 16)

## Why this matters

Your models define what the schema *should* be; migrations define how to *get there* — as ordered, versioned, reviewable steps in git. That's what lets a teammate's clone, CI, staging, and production all reach the identical schema by running the same history; what makes deploys repeatable instead of "run this ALTER by hand"; and what gives you a tested path *backwards* when a deploy goes wrong. `Base.metadata.create_all()` can only build from scratch — it can't evolve a database that's already full of production data. Migrations can.

---

## Setup: the async template

Alembic needs the async variant of its scaffolding, because your engine speaks asyncpg:

```bash
uv add alembic
uv run alembic init -t async alembic
```

This creates `alembic.ini` (config), and `alembic/` containing `env.py` (how Alembic connects and what it compares against) and `versions/` (the migration files — your schema's git history).

---

## Configuring `env.py`

Two edits make Alembic yours: point it at your **metadata** (so autogenerate can diff models vs database) and your **settings** (so the DB URL comes from the environment, never hardcoded in `alembic.ini`):

```python
# alembic/env.py — add near the top
from app.core.config import settings
from app.db.base import Base
from app.models import click_event, link, tag  # noqa: F401 — must import so
                                               # every table registers on Base.metadata

# replace `target_metadata = None` with:
target_metadata = Base.metadata

# inject the URL from settings (overrides alembic.ini):
config.set_main_option("sqlalchemy.url", settings.database_url)
```

That `# noqa` import line matters more than it looks: `Base.metadata` only knows about models whose modules have been **imported**. Forget to import a model here and autogenerate concludes the table shouldn't exist — and generates a `drop_table` for it. (Many teams add an `app/models/__init__.py` that imports every model, and import that one module here.)

---

## The workflow: autogenerate → **review** → upgrade

Add `expires_at: Mapped[datetime | None]` to `Link`, then:

```bash
uv run alembic revision --autogenerate -m "add expires_at to links"
```

Alembic connects, diffs `Base.metadata` against the live schema, and writes `versions/xxxx_add_expires_at_to_links.py`:

```python
def upgrade() -> None:
    op.add_column(
        "links",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("links", "expires_at")
```

**Now read it — every time, like a code review.** Autogenerate is a diff heuristic, not a compiler; it reliably gets columns/tables added and removed, and reliably gets these wrong:

- **Renames.** Rename `note` → `description` and autogenerate sees *drop `note`, add `description`* — applying that **deletes the column's data**. You must hand-edit to `op.alter_column("links", "note", new_column_name="description")`.
- **`server_default` changes** aren't detected by default (see `compare_server_default`), and some **constraint changes** (esp. unnamed constraints, some type changes) are missed or mis-detected.
- It knows *nothing about your data* — adding `nullable=False` to a table with existing rows autogenerates cleanly and then fails at upgrade time on the first existing row.

Then apply, and verify you can go both ways:

```bash
uv run alembic upgrade head        # apply everything up to the latest
uv run alembic downgrade -1        # roll back one revision
uv run alembic upgrade head        # ...and forward again
uv run alembic current             # where is this database?
uv run alembic history             # the whole chain
```

Alembic tracks position in an `alembic_version` table in your database — that's how it knows which migrations a given environment still needs. Testing `downgrade` *now*, while the change is fresh, is what makes rollback a routine operation instead of a 3 a.m. improvisation.

---

## Data migrations

Schema changes sometimes require *data* changes to be valid — the classic: add a column as nullable, backfill it, then tighten to `NOT NULL`. Alembic migrations are Python; they can execute any SQL:

```python
import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    # 1. schema: add nullable first — NOT NULL would fail on existing rows
    op.add_column("links", sa.Column("is_active", sa.Boolean(), nullable=True))

    # 2. data: backfill existing rows
    op.execute("UPDATE links SET is_active = true WHERE is_active IS NULL")

    # 3. schema: now every row complies — tighten the constraint
    op.alter_column("links", "is_active", nullable=False)


def downgrade() -> None:
    op.drop_column("links", "is_active")
```

- **`op.execute(...)`** runs raw SQL — right for most backfills.
- **`op.get_bind()`** returns the migration's connection when you need to *read* and make decisions — e.g. `rows = op.get_bind().execute(sa.text("SELECT id, slug FROM links")).fetchall()`, then loop and issue updates. (This is how the gate's dedupe-then-constrain migration works.)
- **Never import your models into a migration.** Models describe *today's* schema; the migration runs against *yesterday's*. The moment the model evolves past this revision, the import selects columns that don't exist yet at this point in history. Raw SQL / `sa.table()` snapshots only.
- Note the honest `downgrade()`: it undoes the *schema*. Backfilled or rewritten data usually can't be un-rewritten — data steps are often one-way, and the downgrade should restore the schema and say so in a comment.

---

## Migration discipline

Rules that keep a shared migration history sane:

- **One logical change per revision.** "add expires_at" and "create tags tables" are two revisions. Small revisions review cleanly, and when one deploy step fails, you roll back *that step* — not an unrelated change riding along in the same file.
- **Never edit a migration that has been applied anywhere** — a teammate's machine, CI, staging count. Their `alembic_version` says it already ran; your edit will never execute there, and environments silently diverge. Fix forward: write a *new* revision that corrects the mistake. (Only truly unshipped, unpushed migrations are yours to edit.)
- **Migrations run in deploy, before the new code serves traffic** — `alembic upgrade head` as a release step, so code never meets a schema it doesn't expect.
- **Autogenerate proposes; you approve.** The generated file is a draft. Review the diff, fix renames, add data steps, verify the downgrade.

---

## Recap & next

- ✅ Migrations version-control the schema: every environment replays the same ordered history — repeatable deploys, tested rollbacks.
- ✅ `alembic init -t async`; `env.py` gets `target_metadata = Base.metadata` (import **all** model modules!) and the URL from settings.
- ✅ `revision --autogenerate` then **review**: renames appear as drop+add (data loss!), server-default and some constraint changes are missed, and it's blind to existing data.
- ✅ Data migrations: `op.execute()` for SQL, `op.get_bind()` to read and decide; nullable → backfill → `NOT NULL`; never import models.
- ✅ One logical change per revision; never edit an applied migration — fix forward.
- ✅ Self-check: why does renaming a column via autogenerate destroy data, and what's the correct migration?

→ Next: **[Section 06 · Clean architecture](../06_clean_architecture/README.md)**

## Exercises

1. Rename `Link.note` to `Link.description` in the model, run `alembic revision --autogenerate`, and read the generated file *without applying it*. What did Alembic generate, what would applying it do to production data, and what should the migration say instead?

<details>
<summary>Solution</summary>

Autogenerate produces `op.drop_column("links", "note")` + `op.add_column("links", sa.Column("description", ...))` — it can't know the two are the same column. Applying it drops `note` **with all its data**, then adds an empty `description`. Hand-edit to `op.alter_column("links", "note", new_column_name="description")` (and the mirror rename in `downgrade()`), which preserves every value. This is the single best argument for reviewing every autogenerated file.
</details>

2. Write the migration that adds `NOT NULL` column `referrer_domain` (String(255)) to `click_events`, backfilled from the existing `referrer` column (`NULL` referrer → `'unknown'`). Verify `upgrade` and `downgrade` both run on a table with existing rows.

<details>
<summary>Solution</summary>

Three-step pattern: `op.add_column("click_events", sa.Column("referrer_domain", sa.String(255), nullable=True))`, then `op.execute("UPDATE click_events SET referrer_domain = COALESCE(split_part(split_part(referrer, '//', 2), '/', 1), 'unknown')")` followed by `op.execute("UPDATE click_events SET referrer_domain = 'unknown' WHERE referrer_domain IS NULL OR referrer_domain = ''")`, then `op.alter_column("click_events", "referrer_domain", nullable=False)`. Downgrade: `op.drop_column("click_events", "referrer_domain")`. Adding it `NOT NULL` in one step would fail immediately on any existing row.
</details>

3. A teammate notices a typo in a column name in last week's migration — already applied to staging — and pushes a commit editing that migration file. Staging now differs from a fresh CI database. Explain the mechanism, and the correct fix.

<details>
<summary>Solution</summary>

Staging's `alembic_version` records that revision as applied, so the edited file never re-runs there — staging keeps the typo'd column. A fresh CI database replays the *edited* file and gets the corrected name. Same revision id, two different schemas: silent divergence, and the next autogenerate produces different diffs per environment. Correct fix: revert the edit, add a **new** revision with `op.alter_column(..., new_column_name=...)` — fix forward, so every environment converges by running the same history.
</details>
