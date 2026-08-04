"""Aggregate all v1 routers under /api/v1."""
from fastapi import APIRouter

from app.api.v1 import auth, health, projects, tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
