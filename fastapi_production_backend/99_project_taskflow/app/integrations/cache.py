"""Cache-aside helper for read-heavy endpoints (see the other FastAPI course's
Section 06 for the full Redis-scaling treatment)."""
import json
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as redis


async def cache_aside(
    r: redis.Redis, key: str, ttl: int, producer: Callable[[], Awaitable[Any]]
) -> tuple[Any, str]:
    """Return (value, 'HIT'|'MISS'). JSON-serializes the produced value."""
    cached = await r.get(key)
    if cached is not None:
        return json.loads(cached), "HIT"
    value = await producer()
    await r.set(key, json.dumps(value), ex=ttl)
    return value, "MISS"
