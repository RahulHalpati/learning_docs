# 07-1 · Redis caching

> **Level:** Intermediate · **Prerequisites:** [03-3 · CRUD endpoints & pagination](../03_schemas_and_crud/03_crud_endpoints_pagination.md)
> **Time:** 30 min · **Verified:** 2026-07-27 (redis-py 5.3.1, Redis server 6.0.16)

## Why this matters

Read-heavy endpoints hit the database over and over for the same answer. **Caching** in Redis — a store every worker shares — serves the repeat reads in microseconds and takes load off Postgres. The pattern is **cache-aside**, and it's the first performance lever you reach for.

> For the full Redis-scaling treatment (pub/sub, sessions, WebSocket fan-out), see the [async course's Section 06](../../fastapi_async_websockets/README.md). Here we apply the essentials to TaskFlow.

---

## A shared Redis client

Reuse one pooled, async client across the app:

```python
# app/integrations/redis_client.py
import redis.asyncio as redis
from app.core.config import settings

_client: redis.Redis | None = None

def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client
```

---

## Cache-aside

Check the cache; on a miss, produce the value and store it with a **TTL**:

```python
# app/integrations/cache.py
import json

async def cache_aside(r, key, ttl, producer):
    cached = await r.get(key)
    if cached is not None:
        return json.loads(cached), "HIT"
    value = await producer()                    # the expensive DB call
    await r.set(key, json.dumps(value), ex=ttl)  # cache with TTL
    return value, "MISS"
```

```python
calls = {"n": 0}
async def produce():        # stands in for a DB query
    calls["n"] += 1; return {"v": 42}

print(await cache_aside(r, "k", 60, produce))   # (..., 'MISS')
print(await cache_aside(r, "k", 60, produce))   # (..., 'HIT')
print("producer calls:", calls["n"])
```

**Output (real run):**
```
({'v': 42}, 'MISS')
({'v': 42}, 'HIT')
producer calls: 1
```

The producer ran **once** across two requests; the second was served from Redis. At scale, all workers share this cache — a value computed by one serves them all.

---

## What (and what not) to cache

| Cache | Don't cache |
|-------|-------------|
| Read-heavy, rarely-changing data (a dashboard, a public list) | Per-request-unique or write paths |
| Expensive aggregates | Data that must always be exactly current |
| Idempotent GETs | Anything with side effects |

For TaskFlow, a good candidate is a project's task-count summary. **Invalidate** on write: when a task changes, `await r.delete(cache_key)` — or let the TTL bound staleness.

> ⚠️ **Caching adds a correctness risk: stale data.** If you cache a list and then a row changes, the cache is wrong until it's invalidated or expires. Always pair a cache with an invalidation strategy (delete-on-write) or a short TTL, and never cache data that must be to-the-second accurate. A cache bug shows up as "why is it showing the old value?".

---

## Recap & next

- ✅ **Cache-aside**: check Redis → HIT returns it; MISS produces + stores with a **TTL**.
- ✅ A shared, pooled async client; all workers share the cache.
- ✅ Cache read-heavy, rarely-changing GETs; **invalidate on write** or use short TTLs.
- ✅ Never cache must-be-current or side-effecting data.
- ✅ Self-check: what's the risk introduced by caching, and the two ways to bound it?

→ Next: **[07-2 · Rate limiting](02_rate_limiting.md)**

## Exercises

1. Cache a `GET /projects/{id}/summary` (task counts) with a 30s TTL, and invalidate it whenever a task in that project is created/updated/deleted.

<details>
<summary>Solution</summary>

Wrap the summary query in `cache_aside(r, f"summary:{pid}", 30, producer)`; in the task service's create/update/delete, `await r.delete(f"summary:{pid}")`. Reads are fast and shared; writes keep them correct.
</details>
