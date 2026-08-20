# 08-3 · Background jobs with Arq

> **Level:** Intermediate · **Prerequisites:** [08-2 · Rate limiting & sessions](02_rate_limiting_sessions.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (redis-py asyncio · Arq · Redis 7)

## Why this matters

Registration should take 50 ms; sending the welcome email takes 2–8 s of someone else's SMTP server. Making users wait on email, webhooks, or thumbnail generation buys you nothing and couples your latency (and your error rate) to every third party you talk to. The fix is architectural: the request *records intent* and returns; a separate worker process *does the slow thing* — with retries, and without a slow provider tying up the request workers that keep your API alive. That separation is also a blast-radius boundary: an email-provider outage becomes a growing queue, not a growing pile of 500s.

---

## Why not `BackgroundTasks`?

FastAPI ships an in-process option:

```python
@router.post("/auth/register")
async def register(..., background_tasks: BackgroundTasks):
    user = ...
    background_tasks.add_task(log_signup, user.id)  # runs after the response is sent
    return user
```

Know its real limits before trusting it with anything that matters:

- **In-process** — the task lives and dies with the web worker. A deploy, crash, or pod eviction between response and task = task silently lost. There is no queue to pick it back up.
- **No retries** — an exception is logged and that's the end of it.
- **No visibility** — no queue depth, no failure counts, nothing to alert on.
- **Shares the event loop** — heavy tasks steal capacity from live requests.

Verdict: fine for fire-and-forget logging or metrics where a lost task costs nothing. Anything a user would *notice* missing — email, webhook, billing event — needs a real queue.

---

## Arq: the worker

**Arq** is a Redis-backed job queue that's async-native: job functions are plain `async def`, sharing the idioms (and the Redis) you already have. `uv add arq`. The worker is configured by a settings class:

```python
# app/worker.py
import logging

from arq.connections import RedisSettings
from arq.worker import Retry

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_welcome_email(ctx: dict, user_id: int, email: str) -> None:
    # ctx = shared worker state + job metadata; ctx["job_try"] is the attempt number
    logger.info("welcome email -> %s (user %s), attempt %d", email, user_id, ctx["job_try"])
    # A real SMTP call goes here. On a *transient* failure, ask for a retry with backoff:
    #   raise Retry(defer=ctx["job_try"] * 10)   # retry in 10 s, then 20 s, then 30 s...


class WorkerSettings:
    functions = [send_welcome_email]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_tries = 5   # stop retrying after 5 attempts — never retry forever
```

Run it as its **own process**, next to (not inside) the API:

```bash
uv run arq app.worker.WorkerSettings
```

Separate process means separate scaling: email backlog growing? Add workers, not web replicas.

**Retry semantics, precisely:** raising `Retry(defer=seconds)` re-queues the job (up to `max_tries`) — that's for failures you *expect* to heal, like a provider hiccup. An ordinary unhandled exception marks the job **failed**, result recorded, no retry — so wrap transient errors deliberately. And if the worker is killed mid-job, the job is re-run on restart; that "runs again after partially running" case is why idempotency (below) is not optional.

---

## Enqueueing from the API

The API needs an Arq connection pool — created once in lifespan, exactly like the Redis client in 08-1:

```python
# in lifespan, alongside app.state.redis
from arq import create_pool
from arq.connections import RedisSettings

app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
yield
await app.state.arq.aclose()
```

```python
# app/api/deps.py
from arq.connections import ArqRedis

def get_arq(request: Request) -> ArqRedis:
    return request.app.state.arq

ArqDep = Annotated[ArqRedis, Depends(get_arq)]
```

```python
@router.post("/auth/register", status_code=201)
async def register(payload: UserCreate, db: DbSession, arq: ArqDep) -> UserOut:
    user = await create_user(db, payload)
    # The job name is a STRING — the API never imports worker code,
    # so web and worker deploy and scale as independent services.
    await arq.enqueue_job("send_welcome_email", user.id, user.email)
    return user
```

Registration now returns in milliseconds regardless of what SMTP is doing. Keep job **arguments small and primitive** (ids, not ORM objects) — they're serialized into Redis, and the job should re-fetch fresh state from the DB anyway: by the time it runs, the row may have changed.

---

## Cron jobs

Recurring work — purging expired links, rebuilding stats — belongs in the same worker:

```python
from arq import cron

async def purge_expired_links(ctx: dict) -> None:
    """Delete links whose expires_at has passed."""
    ...  # open a session, DELETE WHERE expires_at < now()


class WorkerSettings:
    functions = [send_welcome_email]
    cron_jobs = [cron(purge_expired_links, hour=3, minute=0)]  # 03:00 UTC daily
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_tries = 5
```

Arq coordinates through Redis, so even with several worker replicas each cron fires once per schedule — no "every replica ran the cleanup" surprises.

---

## Idempotency: jobs WILL run twice

At-least-once delivery is the honest contract of every real queue: a worker killed after the side effect but before acknowledging, a user double-submitting, you re-enqueueing during an incident — eventually, every job runs twice. Exactly-once *execution* is not achievable; exactly-once *effect* is, if you design for it:

- **Deduplicate at enqueue** with `_job_id`: `await arq.enqueue_job("send_welcome_email", user.id, email, _job_id=f"welcome:{user.id}")` — Arq refuses a second enqueue (returns `None`) while a job with that id is queued or running.
- **Upsert, don't insert** — `INSERT ... ON CONFLICT DO UPDATE` (05-3) makes a re-run converge instead of crash or duplicate.
- **Set, don't increment** — a job that does `count += 1` double-counts on re-run; a job that computes and *sets* the value lands on the same answer twice.
- **Check-then-act on a marker** — for external side effects like email: record "sent" (a Redis `SET NX` or a DB flag) and skip if already marked. The window between send and mark never fully closes — that's the theory limit — but it shrinks from "whole job" to microseconds.

---

## When Celery instead?

**Celery** is the incumbent, and sometimes the right call: a large existing ecosystem and team familiarity, a *sync* codebase (the classic Django + Celery stack), or genuinely advanced needs — multi-queue routing, priorities, complex workflows (chains/chords), RabbitMQ as broker, Flower for monitoring. Its costs are the mirror image: sync-first design (asyncio support remains bolted-on), and a heavier operational surface (broker + result backend + a zoo of tuning knobs). For an async FastAPI service that already runs Redis, Arq does the same core job with a fraction of the moving parts — reach for Celery when you inherit it or when you outgrow simple queues, not by default.

---

## Recap & next

- ✅ `BackgroundTasks` is in-process: dies with the worker, no retry, no queue visibility — fire-and-forget logging only.
- ✅ Arq: `async def job(ctx, ...)` + `WorkerSettings` (`functions`, `redis_settings`, `max_tries`); run with `uv run arq app.worker.WorkerSettings` as a separate, separately-scalable process.
- ✅ Enqueue via a lifespan-created pool: `enqueue_job("name", *args)` — string names keep API and worker decoupled; pass ids, not objects.
- ✅ `Retry(defer=...)` for transient failures; unhandled exception = failed, not retried; killed mid-job = re-run — so design **idempotent** jobs (`_job_id`, upserts, markers).
- ✅ `cron(...)` for schedules; Celery only when its ecosystem or sync context earns its ops weight.
- ✅ Self-check: your welcome-email job crashed *after* the SMTP send but *before* finishing, and was re-run. What stops the user getting two emails?

→ Next: **[08-4 · Pub/sub & cross-worker real-time](04_pubsub_realtime.md)**

## Exercises

1. Make the welcome email enqueue-idempotent with `_job_id`, then prove the dedup: enqueue it twice for the same user and inspect the return values.

<details>
<summary>Solution</summary>

```python
job1 = await arq.enqueue_job("send_welcome_email", user.id, user.email,
                             _job_id=f"welcome:{user.id}")
job2 = await arq.enqueue_job("send_welcome_email", user.id, user.email,
                             _job_id=f"welcome:{user.id}")
assert job1 is not None and job2 is None
```

The second call returns `None`: Arq sees a job with id `welcome:{user.id}` already queued/running and refuses the duplicate. Note the guard only holds while the first job is in flight — once it completes, the id is free again, so `_job_id` handles *double-enqueue* races, not all re-runs; the marker pattern covers the rest.
</details>

2. Add a cron job that purges expired links every 15 minutes instead of nightly.

<details>
<summary>Solution</summary>

```python
cron_jobs = [cron(purge_expired_links, minute={0, 15, 30, 45})]
```

Set-valued fields mean "at each of these values"; leaving `hour` unset means every hour. Worth pausing on the trade: 96 runs/day of a cheap indexed `DELETE` is fine, but as frequency rises, cron starts imitating a poll loop — if you need near-real-time expiry, filter `expires_at` in the *read* query (expired links simply stop resolving) and let a lazy nightly cron do the physical deletes.
</details>

3. The self-check, worked: the welcome-email job ran, sent the email, then the worker was OOM-killed before the job finished; on restart the job runs again. Write the guard that bounds this to (almost) one email.

<details>
<summary>Solution</summary>

Mark before you're done, check before you act — with Redis you already have:

```python
async def send_welcome_email(ctx: dict, user_id: int, email: str) -> None:
    # NX: returns True only for the FIRST setter — atomic check-and-mark
    first = await ctx["redis"].set(f"sent:welcome:{user_id}", "1", nx=True, ex=86_400)
    if not first:
        return                      # a previous attempt already got this far
    logger.info("welcome email -> %s", email)   # the real send
```

(`ctx["redis"]` is the worker's own connection, provided by Arq.) The re-run now exits immediately. The residual window — killed between the `SET NX` and the send — flips the failure from "maybe two emails" to "maybe zero"; for a welcome email, marking *after* the send (accepting a rare duplicate) is the better trade. Picking which side of that line to err on **is** the idempotency design decision — exactly-once isn't on the menu.
</details>
