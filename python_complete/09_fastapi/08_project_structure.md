# 08 · Industry-Standard Project Structure

> **Level:** Advanced · **Prerequisites:** [07 · Testing](07_testing.md)
> **Time:** ~1 hour · **Verified:** 2026-06-25 (FastAPI 0.136.3)

---

## Why this matters

A single `main.py` works for tutorials but collapses in a team. When routes, models, database logic, and business rules all live in one file, adding a feature means reading the whole thing. Industry projects split by *responsibility* — each layer does one job, and adding a new feature means adding files in predictable places.

---

## The two common layouts

### Flat (layer-based) — small projects

```
app/
├── main.py           # FastAPI app, mounts routers
├── routers/
│   ├── users.py
│   └── items.py
├── models/           # SQLAlchemy ORM models (DB tables)
│   ├── user.py
│   └── item.py
├── schemas/          # Pydantic models (request/response shapes)
│   ├── user.py
│   └── item.py
├── crud/             # Database operations (or "services/")
│   ├── user.py
│   └── item.py
├── core/
│   ├── config.py     # Settings (pydantic-settings)
│   ├── security.py   # Password hashing, JWT
│   └── database.py   # SQLAlchemy engine + session
└── deps.py           # Shared FastAPI dependencies (get_db, get_current_user)
```

### Feature-based — larger projects

```
app/
├── main.py
├── core/             # Cross-cutting concerns
│   ├── config.py
│   ├── database.py
│   └── security.py
└── features/
    ├── users/
    │   ├── router.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── service.py
    │   └── deps.py
    └── items/
        ├── router.py
        ├── models.py
        ├── schemas.py
        └── service.py
```

**Rule of thumb:** start flat. Move to feature-based when any layer folder has >5 files and you're constantly jumping between them to understand one feature.

---

## Build it: a flat project skeleton

We'll build a `bookstore` API throughout modules 08–12. Start with the structure:

```bash
mkdir -p bookstore/app/{routers,models,schemas,crud,core}
touch bookstore/app/__init__.py
touch bookstore/app/{main,deps}.py
touch bookstore/app/routers/{__init__,books,users}.py
touch bookstore/app/models/{__init__,book,user}.py
touch bookstore/app/schemas/{__init__,book,user}.py
touch bookstore/app/crud/{__init__,book,user}.py
touch bookstore/app/core/{__init__,config,database,security}.py
touch bookstore/{requirements.txt,alembic.ini,.env}
```

Final layout:

```
bookstore/
├── .env
├── alembic.ini
├── alembic/                 ← created in module 10
│   ├── env.py
│   └── versions/
├── requirements.txt
└── app/
    ├── __init__.py
    ├── main.py
    ├── deps.py
    ├── core/
    │   ├── config.py        ← module 12
    │   ├── database.py      ← module 09
    │   └── security.py      ← module 11
    ├── models/
    │   ├── book.py          ← module 09
    │   └── user.py          ← module 11
    ├── schemas/
    │   ├── book.py          ← module 09
    │   └── user.py          ← module 11
    ├── crud/
    │   ├── book.py          ← module 09
    │   └── user.py          ← module 11
    └── routers/
        ├── books.py         ← module 09
        └── users.py         ← module 11
```

---

## The key separation: models vs schemas

This is the most common point of confusion.

| File | Class type | Purpose |
|---|---|---|
| `models/book.py` | SQLAlchemy `Base` | Defines the **database table** structure |
| `schemas/book.py` | Pydantic `BaseModel` | Defines the **API shape** (request/response JSON) |

They look similar but serve different roles:

```python
# models/book.py — maps to a database table
from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)  # stored in pence/cents
    is_published = Column(Boolean, default=True)
```

```python
# schemas/book.py — defines what the API accepts/returns
from pydantic import BaseModel, Field

class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)
    price: int = Field(gt=0, description="Price in pence")

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    price: int
    is_published: bool

    model_config = {"from_attributes": True}   # allow .model_validate(orm_obj)
```

Why keep them separate? The database model has columns you never expose in the API (e.g., `hashed_password`, `internal_flags`). The schema enforces validation rules the DB doesn't know about. They evolve independently.

---

## Router pattern

Each resource gets its own router file. `main.py` just mounts them:

```python
# app/routers/books.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app import deps
from app.schemas.book import BookCreate, BookResponse
from app.crud import book as crud_book

router = APIRouter(prefix="/books", tags=["books"])

@router.get("/", response_model=list[BookResponse])
async def list_books(db: AsyncSession = Depends(deps.get_db)):
    return await crud_book.get_all(db)

@router.post("/", response_model=BookResponse, status_code=201)
async def create_book(data: BookCreate, db: AsyncSession = Depends(deps.get_db)):
    return await crud_book.create(db, data)
```

```python
# app/main.py
from fastapi import FastAPI
from app.routers import books, users

app = FastAPI(title="Bookstore API", version="1.0.0")

app.include_router(books.router)
app.include_router(users.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## CRUD layer: why it exists

The CRUD layer separates database operations from HTTP concerns. Routers speak HTTP; CRUD functions speak SQLAlchemy. This means:

- Tests can call CRUD functions directly without HTTP overhead
- The same CRUD function can be called from a router, a background task, or a CLI script
- Changing from SQLite to PostgreSQL means editing `database.py` and `crud/`, not touching routers

```python
# app/crud/book.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.book import Book
from app.schemas.book import BookCreate

async def get_all(db: AsyncSession) -> list[Book]:
    result = await db.execute(select(Book).where(Book.is_published == True))
    return result.scalars().all()

async def create(db: AsyncSession, data: BookCreate) -> Book:
    book = Book(**data.model_dump())
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book

async def get_by_id(db: AsyncSession, book_id: int) -> Book | None:
    result = await db.execute(select(Book).where(Book.id == book_id))
    return result.scalar_one_or_none()
```

---

## Common mistakes

**Putting database logic directly in the router:**
```python
# Don't do this — mixes HTTP and DB concerns
@router.get("/{book_id}")
async def get_book(book_id: int, db: AsyncSession = Depends(deps.get_db)):
    result = await db.execute(select(Book).where(Book.id == book_id))  # ← should be in crud/
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(404)
    return book
```

**Using the ORM model as the response model:**
```python
# Don't do this — leaks internal columns (hashed_password, etc.)
@router.get("/", response_model=list[Book])  # Book is the ORM model
```

---

## Recap & next

- ✅ Flat layout: `models/` (DB), `schemas/` (API), `crud/` (queries), `routers/` (HTTP), `core/` (config/DB/auth)
- ✅ Models ≠ schemas — they evolve independently and serve different layers
- ✅ CRUD layer: isolates database calls from HTTP logic
- ✅ Routers mount into `main.py` via `include_router()`

**→ Next: [09 · Database with SQLAlchemy](09_database_sqlalchemy.md)**
