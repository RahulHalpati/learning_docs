# 09 · Database with Async SQLAlchemy

> **Level:** Advanced · **Prerequisites:** [08 · Project structure](08_project_structure.md)
> **Time:** ~2 hours · **Verified:** 2026-06-25 (SQLAlchemy 2.0.41, asyncpg/aiosqlite)

---

## Why this matters

Every production API persists data. SQLAlchemy is the dominant Python ORM — it turns Python classes into database tables and SQL queries into method calls. The 2.0 API with native async support (`AsyncSession`) integrates cleanly with FastAPI's async routes without blocking the event loop.

---

## Install

```bash
pip install "sqlalchemy[asyncio]" "aiosqlite" "greenlet"
# For PostgreSQL instead of SQLite:
# pip install asyncpg
```

---

## Core concepts

```mermaid
flowchart TD
    A[Python code] --> B[SQLAlchemy ORM Model\nclass Book]
    B --> C[AsyncSession\ntransaction boundary]
    C --> D[AsyncEngine\nconnection pool]
    D --> E[(SQLite / PostgreSQL)]
```

| Concept | What it is |
|---|---|
| **Base** | `DeclarativeBase` subclass — all models inherit from it |
| **Model** | Python class that maps to a table; columns are class attributes |
| **AsyncEngine** | Manages the connection pool; one per application |
| **AsyncSession** | One transaction; created per request, committed/rolled-back, closed |
| **sessionmaker** | Factory that creates `AsyncSession` instances |

---

## `app/core/database.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# One engine for the whole app (connection pool)
engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,      # log SQL to stdout (True in dev only)
    future=True,
)

# Factory — call it to get a fresh AsyncSession
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,     # objects stay usable after commit
    autoflush=False,
    autocommit=False,
)

class Base(DeclarativeBase):
    """All ORM models inherit from this."""
    pass
```

`settings.database_url` for SQLite async:
```
# .env
DATABASE_URL=sqlite+aiosqlite:///./bookstore.db
# For Postgres:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bookstore
```

---

## Database models

```python
# app/models/book.py
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)        # pence
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    owner: Mapped["User | None"] = relationship("User", back_populates="books")
```

```python
# app/models/user.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    books: Mapped[list["Book"]] = relationship("Book", back_populates="owner")
```

The `Mapped[T]` annotation style (SQLAlchemy 2.0) gives full IDE type inference — your editor knows that `book.title` is a `str`, not `Any`.

---

## Pydantic schemas

```python
# app/schemas/book.py
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class BookBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)
    price: int = Field(gt=0, description="Price in pence/cents")
    is_published: bool = True

class BookCreate(BookBase):
    pass   # same fields as base for creation

class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    author: str | None = Field(None, min_length=1, max_length=100)
    price: int | None = Field(None, gt=0)
    is_published: bool | None = None

class BookResponse(BookBase):
    id: int
    created_at: datetime
    owner_id: int | None

    model_config = ConfigDict(from_attributes=True)   # allow ORM objects
```

`from_attributes=True` lets Pydantic read values from SQLAlchemy ORM objects (attributes) rather than just dicts.

---

## Session dependency

```python
# app/deps.py
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

FastAPI calls this once per request. The `async with` block handles opening/closing the session. Commit happens after the route returns; rollback on any exception.

---

## CRUD layer

```python
# app/crud/book.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate

async def get_all(db: AsyncSession, skip: int = 0, limit: int = 20) -> list[Book]:
    result = await db.execute(
        select(Book).where(Book.is_published == True).offset(skip).limit(limit)
    )
    return list(result.scalars().all())

async def get_by_id(db: AsyncSession, book_id: int) -> Book | None:
    result = await db.execute(select(Book).where(Book.id == book_id))
    return result.scalar_one_or_none()

async def create(db: AsyncSession, data: BookCreate, owner_id: int | None = None) -> Book:
    book = Book(**data.model_dump(), owner_id=owner_id)
    db.add(book)
    await db.flush()    # write to DB within transaction, get generated id
    await db.refresh(book)
    return book

async def update(db: AsyncSession, book: Book, data: BookUpdate) -> Book:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(book, field, value)
    await db.flush()
    await db.refresh(book)
    return book

async def delete(db: AsyncSession, book: Book) -> None:
    await db.delete(book)
    await db.flush()
```

Notice `flush()` not `commit()` — the dependency (`get_db`) owns the commit boundary. CRUD functions stay composable: you can call `create()` and `update()` in one route and they're in the same transaction.

---

## Router with DB

```python
# app/routers/books.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app import deps
from app.crud import book as crud_book
from app.schemas.book import BookCreate, BookResponse, BookUpdate

router = APIRouter(prefix="/books", tags=["books"])

@router.get("/", response_model=list[BookResponse])
async def list_books(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(deps.get_db),
):
    return await crud_book.get_all(db, skip=skip, limit=limit)

@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(deps.get_db)):
    book = await crud_book.get_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.post("/", response_model=BookResponse, status_code=201)
async def create_book(data: BookCreate, db: AsyncSession = Depends(deps.get_db)):
    return await crud_book.create(db, data)

@router.patch("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    data: BookUpdate,
    db: AsyncSession = Depends(deps.get_db),
):
    book = await crud_book.get_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return await crud_book.update(db, book, data)

@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: int, db: AsyncSession = Depends(deps.get_db)):
    book = await crud_book.get_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await crud_book.delete(db, book)
```

---

## Testing with an in-memory database

Override the `get_db` dependency with a test session backed by an in-memory SQLite:

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.database import Base
from app.main import app
from app import deps

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)   # create tables
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[deps.get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

```python
# tests/test_books.py
import pytest

@pytest.mark.asyncio
async def test_create_and_get_book(client):
    resp = await client.post("/books/", json={"title": "Fluent Python", "author": "Luciano", "price": 3999})
    assert resp.status_code == 201
    book_id = resp.json()["id"]

    resp = await client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Fluent Python"
```

```bash
pip install pytest-asyncio
# pytest.ini or pyproject.toml:
# [pytest] asyncio_mode = auto
pytest -v
```

---

## Common mistakes

**Calling `await session.commit()` inside CRUD functions:**  
The dependency owns the commit boundary. If CRUD commits mid-transaction, a later failure in the same request doesn't roll back the earlier writes — data inconsistency.

**Reusing `Base.metadata.create_all` for production:**  
`create_all` is fine for development/tests but doesn't handle column renames, constraint changes, or data migrations. That's what Alembic is for — next module.

**`expire_on_commit=False`:**  
By default SQLAlchemy expires all ORM attributes after `commit()` — any access triggers a new SELECT. In async code this causes `MissingGreenlet` errors. Set `expire_on_commit=False` in `async_sessionmaker`.

---

## Exercises

1. **Add a `genre` field.** Add `genre: Mapped[str | None]` to the `Book` model and `genre: str | None = None` to `BookCreate` and `BookResponse`. Verify with a test that creates a book with a genre.

<details>
<summary>Solution</summary>

```python
# models/book.py — add:
genre: Mapped[str | None] = mapped_column(String(50), nullable=True)

# schemas/book.py — add to BookBase:
genre: str | None = Field(None, max_length=50)
```

Then add `genre` to `BookResponse` and run `pytest` — the test will fail because the table is missing the column. This is exactly the problem Alembic (next module) solves without dropping and recreating the table.

</details>

2. **Add `GET /books?author=Luciano`.** Add an optional `author` query parameter to `list_books` that filters by author name (case-insensitive).

<details>
<summary>Solution</summary>

```python
# crud/book.py
async def get_all(db, skip=0, limit=20, author: str | None = None):
    stmt = select(Book).where(Book.is_published == True)
    if author:
        stmt = stmt.where(Book.author.ilike(f"%{author}%"))
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())

# routers/books.py
@router.get("/", response_model=list[BookResponse])
async def list_books(
    skip: int = 0, limit: int = 20,
    author: str | None = None,
    db: AsyncSession = Depends(deps.get_db),
):
    return await crud_book.get_all(db, skip=skip, limit=limit, author=author)
```

</details>

---

## Recap & next

- ✅ `Base` → models → tables; `AsyncSession` → one transaction per request
- ✅ Models (SQLAlchemy) ≠ schemas (Pydantic) — different layers, both needed
- ✅ CRUD layer owns queries; router layer owns HTTP; dependency owns commit/rollback
- ✅ `expire_on_commit=False` is required for async SQLAlchemy
- ✅ Test with in-memory SQLite + dependency override — no external DB needed

**→ Next: [10 · Alembic migrations](10_alembic_migrations.md)**
