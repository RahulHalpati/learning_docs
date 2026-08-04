"""Project service — enforces ownership on every operation."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.project import Project
from app.models.user import User
from app.models.enums import Role
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.repo = ProjectRepository(session)

    async def _owned(self, project_id: int, user: User) -> Project:
        project = await self.repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        # Owner or admin may act; everyone else is denied.
        if project.owner_id != user.id and user.role != Role.admin:
            raise PermissionDeniedError("You do not have access to this project.")
        return project

    async def create(self, data: ProjectCreate, user: User) -> Project:
        return await self.repo.create(
            Project(name=data.name, description=data.description, owner_id=user.id)
        )

    async def get(self, project_id: int, user: User) -> Project:
        return await self._owned(project_id, user)

    async def list(self, user: User, page: int, size: int):
        return await self.repo.list_for_owner(user.id, page, size)

    async def update(self, project_id: int, data: ProjectUpdate, user: User) -> Project:
        project = await self._owned(project_id, user)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await self.repo.session.flush()
        return project

    async def delete(self, project_id: int, user: User) -> None:
        project = await self._owned(project_id, user)
        await self.repo.delete(project)
