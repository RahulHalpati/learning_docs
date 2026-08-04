"""Import all models so Alembic's autogenerate and Base.metadata see them."""
from app.models.project import Project
from app.models.task import Task
from app.models.user import User

__all__ = ["User", "Project", "Task"]
