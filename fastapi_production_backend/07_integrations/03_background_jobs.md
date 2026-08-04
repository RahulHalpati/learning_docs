# 07-3 · Background jobs (arq)

> **Level:** Intermediate · **Prerequisites:** [07-1 · Redis caching](01_redis_caching.md)
> **Time:** 30 min · **Verified:** 2026-07-27 (arq 0.28.0, redis-py 5.3.1)

## Why this matters

Some work is too slow to do inside a request: send a welcome email, generate a report, call a rate-limited third party. Do it in the handler and the client waits (and your worker is blocked). A **job queue** fixes this: the request *enqueues* a task and returns instantly; a separate **worker** does the work. **arq** is a small async queue on Redis — a natural fit for FastAPI.

> FastAPI's built-in `BackgroundTasks` runs work in the *same* process after the response — fine for trivial fire-and-forget. arq runs it in a *separate* process, so it survives restarts, scales independently, and retries. Use `BackgroundTasks` for tiny things; arq for real work.

---

## Define a task + worker

```python
# app/integrations/tasks.py
from arq.connections import RedisSettings
from app.core.config import settings

async def send_welcome_email(ctx, user_id: int, email: str) -> str:
    result = f"welcome email queued for {email} (user {user_id})"
    await ctx["redis"].set(f"welcome:{user_id}", result, ex=3600)   # arq gives ctx["redis"]
    return result

class WorkerSettings:
    functions = [send_welcome_email]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
```

Run the worker as its own process (its own container in compose):

```bash
arq app.integrations.tasks.WorkerSettings
```

---

## Enqueue from an endpoint

Create an arq pool at startup and enqueue from a handler — returning immediately:

```python
from arq import create_pool
from arq.connections import RedisSettings

# in lifespan:
#   app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))

@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: UserCreate, db: DbSession, request: Request):
    user = await AuthService(db).register(data)
    await request.app.state.arq.enqueue_job("send_welcome_email", user.id, user.email)
    return user            # responds NOW; the email is sent by the worker
```

Registration returns in milliseconds; the (slow) email happens out-of-band. Verified round-trip (enqueue → worker processes → result stored):

**Output (real run, arq burst worker):**
```
enqueued job id: 89e6e59e ...
job result: welcome email queued for a@b.com (user 1)
```

---

## What arq gives you free

| Feature | Why it matters |
|---------|----------------|
| **Retries** | a failing job re-runs with backoff |
| **Cron / scheduled** | periodic jobs (nightly reports) via `cron()` |
| **Result storage** | fetch a job's result/status later |
| **Horizontal scale** | run more worker processes; they share the queue |

You'd otherwise hand-roll all of this. Scale throughput by adding workers — they pull from the same Redis queue.

> **Tip — the worker is a separate deployable.** In `docker-compose.yml` the `worker` service runs `arq app.integrations.tasks.WorkerSettings` alongside the `api`. They share the code image and Redis but scale independently — burst the workers during a heavy report run without touching the API.

---

## When to use what

| Need | Use |
|------|-----|
| Trivial fire-and-forget after response | FastAPI `BackgroundTasks` |
| Real slow work, retries, own scaling | **arq** |
| Heavy/legacy Python ecosystems | Celery (bigger, sync-rooted) |
| Guaranteed delivery / complex routing | a real broker (RabbitMQ/Kafka) |

For an async FastAPI + Redis stack, arq is the natural first choice.

---

## Recap & next

- ✅ Slow work → a **background job**: the request enqueues and returns; a **worker** does it.
- ✅ arq: define tasks + `WorkerSettings`, run `arq ...WorkerSettings`, enqueue via a pool.
- ✅ Free retries, cron, result storage; scale by adding worker processes.
- ✅ `BackgroundTasks` for trivial in-process work; arq (separate process) for real work.
- ✅ Self-check: what does the *client* wait for with an in-handler email vs an arq-enqueued one?

→ Next: **[08 · Observability & ops](../08_observability_and_ops/README.md)**

## Exercises

1. Enqueue `send_welcome_email` from the register endpoint, run the worker, and read back `welcome:{user_id}` from Redis to confirm it ran.

<details>
<summary>Solution</summary>

Add the arq pool to lifespan, `enqueue_job(...)` in `register`, run `arq app.integrations.tasks.WorkerSettings`, then `redis-cli get welcome:1`. Registration stayed instant; the worker did the (pretend) email out-of-band.
</details>
