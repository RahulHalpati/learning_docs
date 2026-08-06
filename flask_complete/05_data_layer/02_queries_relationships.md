# 05-2 · Queries & relationships

> **Level:** Intermediate · **Prerequisites:** [05-1 · Models with Flask-SQLAlchemy](01_models_sqlalchemy.md)
> **Time:** 50 min · **Verified:** 2026-07-29 (Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.51)

## Why this matters

Reading and writing data is most of what an app does. SQLAlchemy 2.0's `select()` style is the current standard — worth learning properly, since most tutorials still show the legacy `Model.query` API.

---

## Write: add, commit

```python
user = User(email="ada@example.com")
db.session.add(user)
db.session.commit()                       # writes it; user.id is now populated

db.session.add_all([Note(title=f"n{i}", user_id=user.id) for i in range(5)])
db.session.commit()
```

`db.session` is the unit of work: stage changes with `add()`, persist with `commit()`, undo with `rollback()`.

---

## Read

```python
from sqlalchemy import select, func

db.session.get(User, 1)                                    # by primary key (fastest)
db.session.scalar(select(User).filter_by(email="ada@example.com"))     # one or None
db.session.scalars(select(Note).order_by(Note.id.desc())).all()        # a list
db.session.scalar(select(func.count()).select_from(Note))              # a count
```

**Output (real run):**
```
get:            ada@example.com
scalar filter:  1
scalars all:    ['n4', 'n3', 'n2', 'n1', 'n0']
count:          5
```

The three you'll use constantly:

| Call | Returns |
|------|---------|
| `db.session.get(Model, pk)` | one object or `None` (by primary key) |
| `db.session.scalar(select(...))` | the first result or `None` |
| `db.session.scalars(select(...)).all()` | a list of objects |

Filtering: `.filter_by(email=...)` for simple equality, `.where(Note.title.like("%milk%"))` for anything else. Chain `.order_by()`, `.limit()`, `.offset()`.

> **Legacy vs modern.** `Note.query.filter_by(...).all()` is the old Flask-SQLAlchemy API — still functional, but the `select()` form above is the SQLAlchemy 2.0 standard and what new code uses. Recognize both; write the new one.

---

## Relationships

Declared relationships are just attributes:

```python
user.notes                # -> [Note, Note, ...]
note.author.email         # -> "ada@example.com"
```

**Output (real run):**
```
relationship: ['n0', 'n1']  | back: ada@example.com
```

### The N+1 problem

```python
for note in db.session.scalars(select(Note)).all():
    print(note.author.email)          # ⚠️ one extra query PER note
```

That's 1 query for the notes plus N for the authors — fine with 5 notes, a disaster with 5,000. Fix it by loading them together:

```python
from sqlalchemy.orm import selectinload
notes = db.session.scalars(
    select(Note).options(selectinload(Note.author))       # 2 queries total
).all()
```

> ⚠️ **N+1 is the most common ORM performance bug.** It hides in loops and templates (a `{% for note in notes %}{{ note.author.email }}{% endfor %}` triggers it too). If a page gets slow as data grows, check for it first. `selectinload` (or `joinedload`) is the fix.

---

## Pagination

Flask-SQLAlchemy adds `db.paginate()`:

```python
p = db.paginate(select(Note).order_by(Note.id), page=1, per_page=2, error_out=False)
p.items, p.total, p.pages, p.page, p.has_next
```

**Output (real run, 5 notes, per_page=2):**
```
paginate: ['n0', 'n1']   total: 5   pages: 3
```

`error_out=False` returns an empty page instead of 404 for an out-of-range page. **Always** bound `per_page` from user input (FlaskNotes caps it at 100) — otherwise `?per_page=1000000` is a denial-of-service.

---

## Deleting & cascades

```python
db.session.delete(user)
db.session.commit()
```

**Output (real run):**
```
cascade deleted notes: 0        (the user's 5 notes went with them)
```

That's `cascade="all, delete-orphan"` from the model doing its job — no orphaned rows.

---

## Recap & next

- ✅ Write: `db.session.add()` → `commit()`; read: `get()`, `scalar()`, `scalars().all()`.
- ✅ Use the modern **`select()`** style; recognize legacy `Model.query`.
- ✅ Relationships are attributes — beware **N+1**; fix with `selectinload`.
- ✅ `db.paginate(...)` gives `items/total/pages`; always cap `per_page`.
- ✅ Cascades delete children with their parent.
- ✅ Self-check: a page listing 100 notes with `note.author.email` fires how many queries, and how do you fix it?

→ Next: **[05-3 · Migrations with Flask-Migrate](03_migrations.md)**

## Exercises

1. Write a query for "the 5 most recent notes belonging to user 1", then add `selectinload(Note.author)` and reason about the query count.

<details>
<summary>Solution</summary>

```python
db.session.scalars(
    select(Note).filter_by(user_id=1).order_by(Note.id.desc()).limit(5)
    .options(selectinload(Note.author))
).all()
```
Without the option: 1 + 5 = 6 queries if you touch `.author`. With it: 2. That's the N+1 fix in miniature.
</details>
