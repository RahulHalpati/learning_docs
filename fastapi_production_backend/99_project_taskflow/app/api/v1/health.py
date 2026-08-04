"""Liveness & readiness probes (for Kubernetes / load balancers)."""
from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict:
    """Is the process up? (No dependencies checked — must be cheap.)"""
    return {"status": "ok"}


@router.get("/readyz")
async def readiness(db: DbSession) -> dict:
    """Can we serve traffic? Verify the database is reachable."""
    await db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
