"""Redis-backed integration tests. Skipped automatically if Redis is unreachable."""
import pytest
import redis.asyncio as redis

from app.core.config import settings
from app.integrations.cache import cache_aside


async def _redis_or_skip():
    # A fresh client per test — avoids a cached client bound to a closed event loop.
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.ping()
    except Exception:
        await r.aclose()
        pytest.skip("Redis not reachable — start one to run integration tests.")
    return r


async def test_cache_aside_hit_miss():
    r = await _redis_or_skip()
    await r.flushdb()
    calls = {"n": 0}

    async def produce():
        calls["n"] += 1
        return {"v": 42}

    v1, s1 = await cache_aside(r, "k", 60, produce)
    v2, s2 = await cache_aside(r, "k", 60, produce)
    assert (s1, s2) == ("MISS", "HIT")
    assert v1 == v2 == {"v": 42}
    assert calls["n"] == 1                 # produced once, served twice


async def test_rate_limit_counter():
    import time
    r = await _redis_or_skip()
    await r.flushdb()
    key = f"rl:test:{int(time.time())}"
    allowed = []
    for _ in range(7):
        n = await r.incr(key)
        allowed.append(n <= 5)
    assert allowed == [True] * 5 + [False, False]
