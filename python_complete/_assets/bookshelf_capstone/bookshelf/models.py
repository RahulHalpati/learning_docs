"""Pydantic models — the validated shapes of data in and out."""
from pydantic import BaseModel, Field, field_validator


class BookIn(BaseModel):
    """What a client sends to create/update a book."""
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    isbn: str = Field(min_length=10, max_length=17)
    year: int = Field(ge=1450, le=2100)

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class BookOut(BookIn):
    """What we send back — the input fields plus a server-assigned id."""
    id: int
