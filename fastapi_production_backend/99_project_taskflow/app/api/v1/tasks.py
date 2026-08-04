"""Task routes — nested under a project."""
from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, PageParams
from app.models.enums import TaskStatus
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.task import TaskService

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(project_id: int, data: TaskCreate, user: CurrentUser, db: DbSession):
    return await TaskService(db).create(project_id, data, user)


@router.get("", response_model=Page[TaskRead])
async def list_tasks(
    project_id: int, user: CurrentUser, db: DbSession, page: PageParams,
    status: TaskStatus | None = None,          # optional ?status= filter
):
    items, total = await TaskService(db).list(project_id, user, page.page, page.size, status)
    return Page.create(items, total, page.page, page.size)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(project_id: int, task_id: int, user: CurrentUser, db: DbSession):
    return await TaskService(db).get(project_id, task_id, user)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    project_id: int, task_id: int, data: TaskUpdate, user: CurrentUser, db: DbSession
):
    return await TaskService(db).update(project_id, task_id, data, user)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(project_id: int, task_id: int, user: CurrentUser, db: DbSession) -> None:
    await TaskService(db).delete(project_id, task_id, user)
