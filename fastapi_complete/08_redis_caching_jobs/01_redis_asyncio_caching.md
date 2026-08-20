# 08-1 · Redis & cache-aside caching

> **Level:** Intermediate · **Prerequisites:** [07 · Security & authentication](../07_security_auth/README.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (redis-py asyncio · Arq · Redis 7)

## Why this matters

A slug lookup that hits Postgres costs a network hop plus disk-bound work — single-digit milliseconds on a good day, worse under load. The same lookup against memory costs microseconds. Caching your hottest reads cuts p99 latency *and* shrinks the database's load, which shrinks the blast radius when traffic spikes: the cache absorbs the read storm instead of your one Postgres. The catch is that a cache is a second copy of the truth, and second copies drift — this lesson is as much about invalidation as about speed.

---

## What Redis is good at

Redis is an **in-memory data-structure server**, not just a key-value store:

- **In-memory** — reads and writes complete in microseconds; persistence is optional and secondary. Treat everything in it as *losable*: cache, counters, sessions — things you can rebuild from Postgres or re-issue.
- **Single-threaded command execution** — commands run one at a time, so every single command is atomic. `INCR` is a race-free counter across all your app replicas with zero locks. (Redis 7 uses I/O threads for networking; execution stays single-threaded.)
- **Data structures with TTLs** — strings, hashes, sets, **sorted sets**, all with per-key expiry. The next two lessons build rate limiters and job queues out of these primitives.

Architecturally, Redis's job is **shared state that lives beside your app, not inside it**. This is *the* reason a distributed cache exists at all: a process-local cache like `functools.lru_cache` breaks the moment you run more than one worker. Gunicorn with 4 workers means 4 caches that disagree; invalidating in the process that handled the write does nothing for the other three, and Kubernetes replicas make it worse. Users see the new value on one request and the old value on the next, depending on which worker the load balancer picked. One Redis, shared by every replica, is one cache with one answer.

---

## Connecting: lifespan + dependency

Run Redis locally:

```bash
docker run -p 6379:6379 redis:7-alpine
```

Install the client with `uv add redis` and set `REDIS_URL=redis://localhost:6379/0` in `.env` (add `redis_url` and `cache_ttl_seconds: int = 300` to your settings). One naming trap: older tutorials import `aioredis` — that project is **dead**; it was merged into redis-py in 2022. `redis.asyncio` is the only current async API, and it's the last time we'll mention aioredis.

Same shape as the SQLAlchemy engine: **one client per process** (it manages a connection pool internally), created in lifespan, handed out through a dependency.

```python
# app/core/redis.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from redis.asyncio import Redis

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ONE client per process — it owns a connection pool, like the DB engine.
    # decode_responses=True → you get str back, not bytes; pairs cleanly
    # with Pydantic's JSON strings below.
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.aclose()  # return connections cleanly on shutdown


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


RedisDep = Annotated[Redis, Depends(get_redis)]
```

Unlike DB sessions there's no per-request unit of work to manage, so the dependency just hands out the shared client — no `yield`, no cleanup. Endpoints declare `redis: RedisDep` exactly like `db: DbSession`.

---

## Cache-aside, step by step

**Cache-aside** (lazy caching) is the workhorse pattern: the application checks the cache first and fills it on a miss. The database stays the source of truth; the cache is a disposable copy.

```python
# app/api/routes/links.py
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select

@router.get("/{slug}")
async def resolve(slug: str, redis: RedisDep, db: DbSession):
    key = f"links:{slug}:v1"

    cached = await redis.get(key)                    # 1. try the cache
    if cached is not None:
        link = LinkOut.model_validate_json(cached)   # 2. hit → deserialize, done
        return RedirectResponse(link.url, status_code=307)

    row = await db.scalar(select(Link).where(Link.slug == slug))  # 3. miss → source of truth
    if row is None:
        raise HTTPException(404, "Unknown slug")

    link = LinkOut.model_validate(row)
    await redis.setex(                               # 4. write back, WITH a TTL
        key, settings.cache_ttl_seconds, link.model_dump_json()
    )
    return RedirectResponse(link.url, status_code=307)  # 5. serve
```

Three decisions in those 20 lines deserve names:

- **Serialization** — Redis stores strings, so store the Pydantic model's JSON: `model_dump_json()` in, `model_validate_json()` out. You get validation on the way back for free — a corrupted or outdated cache entry fails loudly instead of leaking garbage into a response.
- **Key naming discipline** — `links:{slug}:v1` is `namespace:identity:schema-version`. The namespace prevents collisions between features sharing one Redis; the version suffix means that when `LinkOut` changes shape, you deploy code reading/writing `:v2` and the stale `:v1` entries simply expire. No cache flush, no migration.
- **`SETEX`, never bare `SET`** — value and TTL land atomically. A key without a TTL is a memory leak with a delay.

**Choosing the TTL:** long enough to absorb the read load, short enough that the staleness is tolerable *for that data*. A redirect target that's 5 minutes stale is fine; a stats counter shown on a dashboard might warrant 30–60 s. TTL is a **staleness bound**, not a correctness mechanism — it caps how long a wrong answer can live, nothing more. Correctness comes next.

---

## Invalidation: delete, don't update

When a link is updated or deleted, its cache entry is now a lie. The rule: **DELETE the key — don't write the new value into the cache.**

```python
async def update_link(slug: str, payload: LinkUpdate, db: DbSession, redis: RedisDep):
    ...  # write the change to Postgres
    await redis.delete(f"links:{slug}:v1")  # invalidate — the next read repopulates
```

Why not just `SETEX` the fresh value? Because updating races with concurrent cache fills: a reader that missed *before* your DB write can finish its fill *after* your cache write, stamping the **old** DB value over your new one — stale until TTL, silently. `DELETE` can't lose that race in a damaging way: the worst outcome is one extra DB read. Deletion is idempotent, cheap, and boring — exactly what you want in an invalidation path. (A tiny race window still exists between the DB commit and the delete; the TTL bounds it, which is one more reason every cached key has one.)

---

## Cache stampede, in one paragraph

When a *hot* key expires, every concurrent request misses at once and they all pile onto the database together — the very load spike the cache existed to prevent, arriving on a timer. Two standard mitigations: a **short lock** (one request takes `SET key:lock NX EX 5` and rebuilds while the others briefly wait or serve the old value), or **jittered TTLs** (`ttl + random.randint(0, 30)` so a batch of keys cached together doesn't expire together). Know the failure mode and its names; build the mitigation only when a real hot key shows up in your metrics.

---

## Recap & next

- ✅ Redis = in-memory, atomic single commands, data structures with TTLs — **shared state across replicas**, which `lru_cache` can never be with >1 worker.
- ✅ One client per process: `Redis.from_url(..., decode_responses=True)` in **lifespan**, injected via `RedisDep`. (`aioredis` is dead — it merged into redis-py.)
- ✅ Cache-aside: read → miss → DB → `SETEX` → return; Pydantic `model_dump_json` / `model_validate_json`; keys as `namespace:identity:version`.
- ✅ Invalidate by **deleting** the key on write — updating it races with concurrent fills. TTL bounds staleness; it doesn't create correctness.
- ✅ Self-check: why does *deleting* the key on update beat *writing the new value* into the cache?

→ Next: **[08-2 · Rate limiting & sessions](02_rate_limiting_sessions.md)**

## Exercises

1. Add cache-aside to `GET /links/{slug}/stats` with key `links:{slug}:stats:v1` and a **60-second** TTL. Why should this TTL be shorter than the redirect cache's?

<details>
<summary>Solution</summary>

Same five steps as `resolve`: `GET` → on miss query the click count → `SETEX` the stats schema's JSON → return; delete the key in the same places that record clicks are written, or accept staleness. The TTL is shorter because stats *change constantly* (every click) and users watch them expecting movement — a 5-minute-frozen counter looks broken, while a 5-minute-stale redirect target is invisible. TTL tracks the data's tolerance for staleness, not a global constant.
</details>

2. Every request for a *nonexistent* slug currently falls through to Postgres — a slug-guessing bot becomes a DB load test. Add **negative caching**: cache the miss too. What's the trade-off?

<details>
<summary>Solution</summary>

On a DB miss, store a sentinel with a short TTL before raising:

```python
if row is None:
    await redis.setex(key, 30, "__missing__")
    raise HTTPException(404, "Unknown slug")
```

and on a cache hit, check for the sentinel first (`if cached == "__missing__": raise HTTPException(404, ...)`). Trade-off: a slug *created* right after a negative entry is cached returns 404 for up to 30 s — so keep the negative TTL much shorter than the positive one, or delete the key when a link is created with that slug (creation is a write: invalidate like any other write).
</details>

3. No code: your team ships `@lru_cache` on the resolver and runs uvicorn with 4 workers. Describe the exact bug a user reports after editing a link's URL.

<details>
<summary>Solution</summary>

The edit invalidates (or repopulates) only the cache in the worker that handled the `PATCH`. The other three workers keep their old entry until process restart — `lru_cache` has no TTL at all. The user reloads the link and the redirect flip-flops between the new and old URL depending on which worker the load balancer picks — roughly 3 of 4 requests wrong, *indefinitely*. That nondeterministic flip-flop is the signature of process-local cache behind a multi-worker server, and it's the reason the cache must live in Redis, outside the processes.
</details>
