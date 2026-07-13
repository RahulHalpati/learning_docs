"""The Bookshelf API — async REST endpoints over the repository."""
from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from typing import Annotated

from .exceptions import BookshelfError
from .models import BookIn, BookOut
from .repository import BookRepository

app = FastAPI(title="Bookshelf API", version="1.0.0")

# one shared repository for the app's lifetime
_repo = BookRepository()


def get_repo() -> BookRepository:
    """Dependency: provides the repository (easy to override in tests)."""
    return _repo


# map ANY domain exception to a clean HTTP response
@app.exception_handler(BookshelfError)
async def handle_bookshelf_error(request: Request, exc: BookshelfError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": type(exc).__name__, "detail": exc.message},
    )


@app.get("/books", response_model=list[BookOut])
async def list_books(repo: Annotated[BookRepository, Depends(get_repo)]):
    return await repo.list_all()


@app.post("/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookIn, repo: Annotated[BookRepository, Depends(get_repo)]):
    return await repo.add(book)


@app.get("/books/{book_id}", response_model=BookOut)
async def get_book(book_id: int, repo: Annotated[BookRepository, Depends(get_repo)]):
    return await repo.get(book_id)


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, repo: Annotated[BookRepository, Depends(get_repo)]):
    await repo.delete(book_id)
