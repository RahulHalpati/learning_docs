"""Domain exceptions for the bookshelf — pure business logic, no HTTP."""


class BookshelfError(Exception):
    """Base class for all bookshelf errors. Carries an HTTP status code."""
    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class BookNotFoundError(BookshelfError):
    status_code = 404

    def __init__(self, book_id: int):
        self.book_id = book_id
        super().__init__(f"no book with id {book_id}")


class DuplicateISBNError(BookshelfError):
    status_code = 409

    def __init__(self, isbn: str):
        self.isbn = isbn
        super().__init__(f"a book with ISBN {isbn} already exists")
