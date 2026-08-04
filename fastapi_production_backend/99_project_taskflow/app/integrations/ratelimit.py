"""Distributed rate limiting as a FastAPI dependency (fixed window in Redis)."""
import time

from fastapi import Depends, Request

from app.core.config import settings
from app.core.exceptions import AppError
from app.integrations.redis_client import get_redis


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"


def rate_limiter(limit: int | None = None, window: int | None = None):
    """Build a dependency that limits `limit` requests per `window` seconds per client IP."""
    limit = limit or settings.rate_limit
    window = window or settings.rate_window

    async def dependency(request: Request) -> None:
        r = get_redis()
        identity = request.client.host if request.client else "anon"
        key = f"rl:{identity}:{int(time.time()) // window}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window)
        if count > limit:
            raise RateLimitError("Rate limit exceeded. Try again later.")

    return Depends(dependency)
