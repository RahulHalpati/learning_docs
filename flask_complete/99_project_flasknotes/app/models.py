"""Database models (SQLAlchemy 2.0 typed style, via Flask-SQLAlchemy)."""
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    notes: Mapped[list["Note"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        # scrypt by default in modern Werkzeug — salted and slow on purpose.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Note(db.Model):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    author: Mapped["User"] = relationship(back_populates="notes")

    def to_dict(self) -> dict:
        """Serialize for the JSON API (never expose the owner's credentials)."""
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "image": self.image,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
