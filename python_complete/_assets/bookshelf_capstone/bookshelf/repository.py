"""An in-memory, async-safe book repository (stands in for a database)."""
import asyncio

from .exceptions import BookNotFoundError, DuplicateISBNError
from .models import BookIn, BookOut


class BookRepository:
    """Stores books in memory. Async methods simulate real I/O latency."""

    def __init__(self) -> None:
        self._books: dict[int, BookOut] = {}
        self._next_id = 1
        self._lock = asyncio.Lock()      # guard the shared dict across tasks

    async def add(self, data: BookIn) -> BookOut:
        async with self._lock:
            if any(b.isbn == data.isbn for b in self._books.values()):
                raise DuplicateISBNError(data.isbn)
            book = BookOut(id=self._next_id, **data.model_dump())
            self._books[book.id] = book
            self._next_id += 1
            return book

    async def get(self, book_id: int) -> BookOut:
        await asyncio.sleep(0)           # yield, as a real async DB would
        if book_id not in self._books:
            raise BookNotFoundError(book_id)
        return self._books[book_id]

    async def list_all(self) -> list[BookOut]:
        await asyncio.sleep(0)
        return list(self._books.values())

    async def delete(self, book_id: int) -> None:
        async with self._lock:
            if book_id not in self._books:
                raise BookNotFoundError(book_id)
            del self._books[book_id]
