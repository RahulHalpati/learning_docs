# 05-1 · Models with Flask-SQLAlchemy

> **Level:** Intermediate · **Prerequisites:** [04-1 · The application factory](../04_app_structure/01_app_factory.md)
> **Time:** 50 min · **Verified:** 2026-07-29 (Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.51)

## Why this matters

**Flask-SQLAlchemy** wires SQLAlchemy — the standard Python ORM — into Flask: it manages the engine, gives each request a session, and ties both to your app config. You define tables as Python classes and work with objects instead of SQL strings.

---

## Setup (the `init_app` pattern)

```python
# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):        # SQLAlchemy 2.0 style
    pass

db = SQLAlchemy(model_class=Base)
```

```python
# app/__init__.py, inside create_app()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///flasknotes.db"
db.init_app(app)
```

> **Flask-SQLAlchemy 3.1 uses the SQLAlchemy 2.0 style.** Older tutorials show `db.Column(db.Integer, primary_key=True)` and `Model.query.filter_by(...)`. Those still work but are **legacy** — this course uses the modern typed `Mapped[...]` / `select()` style you'll see in new codebases.

---

## A model

```python
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db

class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    notes: Mapped[list["Note"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
```

- **`Mapped[int]` vs `Mapped[int | None]`** — the annotation decides `NOT NULL`. Optional type = nullable column.
- **`unique=True, index=True`** on email — enforce uniqueness and make lookups fast.
- **`server_default=func.now()`** — the *database* stamps the time.
- **`db.Model`** — Flask-SQLAlchemy's base; it also auto-derives `__tablename__`, though naming it explicitly is clearer.

## Relationships

```python
class Note(db.Model):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[str | None] = mapped_column(String(255), nullable=True)   # optional
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    author: Mapped["User"] = relationship(back_populates="notes")
```

- **`ForeignKey("users.id", ondelete="CASCADE")`** — the database deletes a user's notes with them.
- **`relationship(back_populates=...)`** on both sides gives you `user.notes` **and** `note.author`.
- **Index the foreign key** — you'll filter on it constantly.

**Output (real run):**
```
relationship: ['n0', 'n1']  | back: ada@example.com
cascade deleted notes: 0        (deleting the user removed all 5 notes)
```

---

## Serialization: keep secrets out

Give models an explicit `to_dict()` for JSON responses:

```python
def to_dict(self) -> dict:
    return {"id": self.id, "title": self.title, "body": self.body,
            "image": self.image, "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None}
```

Explicit is the point: a `User.to_dict()` that never lists `password_hash` **cannot** leak it, no matter who calls it later.

---

## Creating the tables

```python
with app.app_context():
    db.create_all()          # fine for tests/prototypes
```

`create_all()` only creates *missing* tables — it can't alter existing ones and has no history. For anything real, use migrations ([05-3](03_migrations.md)).

---

## Recap & next

- ✅ `SQLAlchemy(model_class=Base)` in `extensions.py`, bound with `db.init_app(app)`.
- ✅ Modern **typed** style: `Mapped[...]` + `mapped_column(...)`; the annotation controls nullability.
- ✅ `ForeignKey(..., ondelete=)` + `relationship(back_populates=)` for relations; index your FKs.
- ✅ Explicit **`to_dict()`** so hashes/secrets can't be serialized by accident.
- ✅ `create_all()` for tests only — migrations in production.
- ✅ Self-check: what's the difference between `Mapped[str]` and `Mapped[str | None]` at the database level?

→ Next: **[05-2 · Queries & relationships](02_queries_relationships.md)**

## Exercises

1. Add a `Tag` model and a many-to-many relationship with `Note` (via an association table).

<details>
<summary>Solution</summary>

Create an association `Table("note_tags", db.metadata, Column("note_id", ForeignKey("notes.id")), Column("tag_id", ForeignKey("tags.id")))`, then `tags: Mapped[list["Tag"]] = relationship(secondary=note_tags, back_populates="notes")` on both sides. Many-to-many always needs that middle table.
</details>
