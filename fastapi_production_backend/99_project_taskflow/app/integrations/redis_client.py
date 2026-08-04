"""Lazy, shared Redis client. Optional — the app runs without it."""
import redis.asyncio as redis

from app.core.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return a process-wide pooled Redis client (created on first use)."""
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client
