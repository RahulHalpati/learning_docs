"""Project repository — list is scoped to the owner (multi-tenant isolation)."""
from sqlalchemy import select

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def list_for_owner(self, owner_id: int, page: int, size: int):
        stmt = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.id.desc())
        )
        return await self._paginate(stmt, page, size)
