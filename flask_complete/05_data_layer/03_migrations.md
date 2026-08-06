# 05-3 · Migrations with Flask-Migrate

> **Level:** Intermediate · **Prerequisites:** [05-1 · Models with Flask-SQLAlchemy](01_models_sqlalchemy.md)
> **Time:** 45 min · **Verified:** 2026-07-29 (Flask-Migrate 4.1.0, alembic 1.19.0)

## Why this matters

`db.create_all()` creates *missing* tables — it can't add a column to a table that already has data. Real schemas change constantly, and you need those changes versioned, reviewable, and repeatable across every environment. **Flask-Migrate** (a Flask wrapper around **Alembic**) is the industry standard for that.

---

## Setup

```python
# app/extensions.py
from flask_migrate import Migrate
migrate = Migrate()

# app/__init__.py, inside create_app()
migrate.init_app(app, db)
```

That adds a `flask db` command group.

---

## The three commands

```bash
export FLASK_APP=wsgi.py

flask db init                              # once per project: create migrations/
flask db migrate -m "initial schema"       # generate a migration from model changes
flask db upgrade                           # apply it to the database
```

**Output (real run — `flask db migrate`):**
```
INFO  [alembic.autogenerate.compare] Detected added table 'users'
INFO  [alembic.autogenerate.compare] Detected added index 'ix_users_email' on '('email',)'
INFO  [alembic.autogenerate.compare] Detected added table 'notes'
INFO  [alembic.autogenerate.compare] Detected added index 'ix_notes_user_id' on '('user_id',)'
```

**Output (real run — `flask db upgrade`):**
```
INFO  [alembic.runtime.migration] Running upgrade  -> e48da8d06bf5, initial schema
```

**Output (real run — the resulting tables):**
```
['alembic_version', 'users', 'notes']
```

`alembic_version` is the bookmark recording which migration the database is at — that's how `upgrade` knows what still needs running.

---

## The everyday loop

```bash
# 1. change a model (add a column, index, table)
# 2. generate
flask db migrate -m "add note.pinned"
# 3. READ the generated file in migrations/versions/
# 4. apply
flask db upgrade
# roll back one step if it was wrong
flask db downgrade
```

> ⚠️ **Always read the generated migration before committing it.** Autogenerate is a *draft*. It reliably catches added/removed tables, columns, and indexes — but it sees a **rename** as "drop the old column, add a new one", which silently destroys that column's data. Rewrite those by hand with `op.alter_column(..., new_column_name=...)`.

Autogenerate also can't see everything (some constraint and type changes). Review, don't trust.

---

## What a migration looks like

```python
# migrations/versions/e48da8d06bf5_initial_schema.py
revision = "e48da8d06bf5"
down_revision = None                 # the chain: each migration points at its parent

def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_users_email", "users", ["email"], unique=True)

def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

Every migration is a linked list node (`down_revision`), giving Alembic an ordered history it can walk forwards or backwards.

> **Tip — commit migrations with the model change.** They belong in the same commit/PR as the code that needs them: reviewers see the schema delta, teammates get it on `git pull`, and deploys apply it. A model change without its migration is a production incident waiting to happen.

---

## In deployment

Run migrations **before** the new code serves traffic. FlaskNotes' container does exactly this:

```dockerfile
CMD ["sh", "-c", "flask db upgrade && gunicorn -w 4 -b 0.0.0.0:8000 'wsgi:app'"]
```

For multi-replica deploys, run `flask db upgrade` as a one-off job first so replicas don't race each other.

---

## Recap & next

- ✅ `flask db init` → `migrate -m "..."` → **read it** → `upgrade`; `downgrade` to roll back.
- ✅ Alembic diffs models vs the database; `alembic_version` tracks where the DB is.
- ✅ Autogenerate misses/mangles some changes — **renames look like drop+add** and lose data.
- ✅ Commit migrations alongside the model change; apply them before serving on deploy.
- ✅ Self-check: why is `db.create_all()` insufficient once your app has real users?

→ Next: **[06 · Auth & sessions](../06_auth_and_sessions/README.md)**

## Exercises

1. Add a `pinned: Mapped[bool]` column with `default=False` to `Note`, generate the migration, read it, apply it, then `flask db downgrade` and confirm the column is gone.

<details>
<summary>Solution</summary>

`flask db migrate -m "add note.pinned"` produces `op.add_column("notes", sa.Column("pinned", sa.Boolean(), ...))`. Note that adding a **non-nullable** column to a table with existing rows needs a server default (or a two-step migration) — the classic autogenerate gotcha.
</details>
