"""Project routes — all scoped to the authenticated owner."""
from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, PageParams
from app.schemas.common import Page
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, user: CurrentUser, db: DbSession):
    return await ProjectService(db).create(data, user)


@router.get("", response_model=Page[ProjectRead])
async def list_projects(user: CurrentUser, db: DbSession, page: PageParams):
    items, total = await ProjectService(db).list(user, page.page, page.size)
    return Page.create(items, total, page.page, page.size)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: int, user: CurrentUser, db: DbSession):
    return await ProjectService(db).get(project_id, user)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: int, data: ProjectUpdate, user: CurrentUser, db: DbSession):
    return await ProjectService(db).update(project_id, data, user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, user: CurrentUser, db: DbSession) -> None:
    await ProjectService(db).delete(project_id, user)
