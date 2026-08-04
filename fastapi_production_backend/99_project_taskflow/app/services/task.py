"""Task service — scoped to a project the user owns."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import TaskStatus
from app.models.task import Task
from app.models.user import User
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.project import ProjectService


class TaskService:
    def __init__(self, session: AsyncSession):
        self.repo = TaskRepository(session)
        self.projects = ProjectService(session)      # reuse ownership checks

    async def create(self, project_id: int, data: TaskCreate, user: User) -> Task:
        await self.projects.get(project_id, user)     # 404/403 if not owned
        return await self.repo.create(
            Task(project_id=project_id, **data.model_dump())
        )

    async def list(self, project_id: int, user: User, page: int, size: int,
                   status: TaskStatus | None = None):
        await self.projects.get(project_id, user)
        return await self.repo.list_for_project(project_id, page, size, status)

    async def _get_in_project(self, project_id: int, task_id: int, user: User) -> Task:
        await self.projects.get(project_id, user)
        task = await self.repo.get(task_id)
        if task is None or task.project_id != project_id:
            raise NotFoundError("Task not found.")
        return task

    async def get(self, project_id: int, task_id: int, user: User) -> Task:
        return await self._get_in_project(project_id, task_id, user)

    async def update(self, project_id: int, task_id: int, data: TaskUpdate, user: User) -> Task:
        task = await self._get_in_project(project_id, task_id, user)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        await self.repo.session.flush()
        return task

    async def delete(self, project_id: int, task_id: int, user: User) -> None:
        task = await self._get_in_project(project_id, task_id, user)
        await self.repo.delete(task)
