"""User schemas — the API contract (never expose the ORM model directly)."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)      # read straight from the ORM object

    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
