"""Test fixtures: an isolated in-memory DB and HTTP clients. No external services."""
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — register models before the app imports
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app


@pytest_asyncio.fixture
async def client():
    # One shared in-memory SQLite (StaticPool keeps a single connection alive).
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_client(client):
    """A client already registered and logged in (Authorization header set)."""
    await client.post("/api/v1/auth/register", json={
        "email": "user@example.com", "password": "password123", "full_name": "Test User",
    })
    tokens = (await client.post("/api/v1/auth/login", data={
        "username": "user@example.com", "password": "password123",
    })).json()
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return client
