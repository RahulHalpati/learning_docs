"""Task repository — list within a project, with optional status filter."""
from sqlalchemy import select

from app.models.enums import TaskStatus
from app.models.task import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def list_for_project(
        self, project_id: int, page: int, size: int, status: TaskStatus | None = None
    ):
        stmt = select(Task).where(Task.project_id == project_id)
        if status is not None:                       # optional filtering
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.id.desc())
        return await self._paginate(stmt, page, size)
