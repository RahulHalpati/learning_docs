"""Generic async repository — the data-access layer.

Repositories know SQL/ORM; services know business rules; the API knows HTTP.
Keeping them separate makes each testable and swappable in isolation.
"""
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id_: int) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()           # assign PK / defaults without committing
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def _paginate(self, stmt, page: int, size: int) -> tuple[list[ModelT], int]:
        total = await self.session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        rows = await self.session.scalars(stmt.limit(size).offset((page - 1) * size))
        return list(rows), int(total or 0)
