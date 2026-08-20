# 11-2 · Compose & runtime: the full stack

> **Level:** Intermediate→Advanced · **Prerequisites:** [11-1 · Docker: multi-stage builds with uv](01_docker_multistage.md)
> **Time:** ~40–50 min · **Verified:** 2026-08-07 (Docker · uv · GitHub Actions)

## Why this matters

One image is not a system. Linkbox needs Postgres, Redis, an arq worker, and a migration step — started in the *right order*, configured without baking secrets anywhere, and shut down without dropping requests. **docker compose** declares all of that in one file, and the runtime concerns it forces you to face — migration ordering, graceful shutdown, liveness vs readiness — are exactly the ones that page people at 3am, on compose and Kubernetes alike.

---

## The compose file

```yaml
# docker-compose.yml
name: linkbox

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-linkbox}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set it in .env}  # fail loudly if unset
      POSTGRES_DB: ${POSTGRES_DB:-linkbox}
    volumes:
      - pg_data:/var/lib/postgresql/data     # named volume — data survives `down`
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-linkbox} -d ${POSTGRES_DB:-linkbox}"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]   # persist the arq queue across redis restarts
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  migrate:
    build: .
    env_file: .env
    command: ["alembic", "upgrade", "head"]  # one-shot: run, exit 0, done
    restart: "no"                            # a migration must never auto-loop
    depends_on:
      postgres:
        condition: service_healthy           # don't migrate a DB that isn't up

  api:
    build: .
    env_file: .env                           # runtime config — never baked into the image
    ports:
      - "8000:8000"
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000",
              "--timeout-graceful-shutdown", "30"]
    stop_grace_period: 35s                   # > uvicorn's drain window, or Docker SIGKILLs mid-drain
    restart: unless-stopped
    depends_on:
      migrate:
        condition: service_completed_successfully   # schema is current BEFORE we serve
      redis:
        condition: service_healthy

  worker:
    build: .                                 # SAME image as api — one artifact, different command
    env_file: .env
    command: ["arq", "app.worker.WorkerSettings"]
    restart: unless-stopped
    depends_on:
      migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy

volumes:
  pg_data:
  redis_data:
```

The startup order is enforced by **health, not sleep-and-hope**: Postgres must answer `pg_isready` → `migrate` runs `alembic upgrade head` and must **exit 0** → only then do `api` and `worker` start. `service_completed_successfully` is the key condition — a failed migration stops the deploy instead of serving traffic against a wrong schema.

---

## Why migrations must NOT run in app startup

The tempting shortcut — `alembic upgrade head` inside the FastAPI lifespan — works with one replica and breaks exactly when it matters:

- **N replicas race the same DDL.** Roll out 3 replicas and all 3 run `upgrade head` at once against one database. Alembic takes a lock, but you get lock contention, timeouts, replicas crash-looping on a half-applied state — during a deploy, the worst possible time.
- **Startup ≠ deploy.** A container restart (OOM, node reboot) re-triggers "migration logic" when nothing changed. Migration is a *deploy event*, not a *process event*.
- **No gate.** If the migration fails inside startup, you find out from a crash-looping app instead of a failed deploy step.

The production pattern, on compose and Kubernetes alike: **deploy = run migrations as a one-shot step, then roll the app.** Our `migrate` service is that step; on k8s it's a Job or pre-deploy hook. The app process only ever *assumes* the schema is current — it never mutates it.

---

## Env & secrets

Two different `.env` roles in that file — don't conflate them:

- **Compose interpolation** (`${POSTGRES_PASSWORD:?…}`): compose reads `.env` *next to the yaml file* to substitute variables in the yaml itself.
- **Runtime env** (`env_file: .env`): injects variables into the *container's* environment, where pydantic-settings picks them up — `DATABASE_URL`, `REDIS_URL`, etc.

Inside the compose network, services reach each other **by service name** — that's the config difference between dev and compose:

```bash
# .env  (gitignored — commit .env.example with dummy values instead)
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+asyncpg://linkbox:change-me@postgres:5432/linkbox   # host = service name
REDIS_URL=redis://redis:6379/0
```

The image from 11-1 contains **zero** configuration — the same image runs in dev, CI, and prod with different env. That's the artifact promise: config varies, the artifact never does.

---

## uvicorn workers vs replicas

One process serves one CPU core's worth of async work. Two ways to scale:

- **On a VM / single host:** `uvicorn app.main:app --workers 4` — uvicorn forks 4 processes behind one socket. Simple and fine for compose-on-a-box.
- **On an orchestrator (the k8s-era pattern):** **one process per container, many replicas** behind a load balancer. The orchestrator owns scaling, health, and placement — per-container workers just blur its per-unit accounting (CPU, memory, probes).

You'll still meet the **legacy pattern** in older codebases: `gunicorn -k uvicorn.workers.UvicornWorker` as a process manager around uvicorn. It predates uvicorn's own `--workers` support; know it to recognize it, don't reach for it in new work.

---

## Graceful shutdown: the SIGTERM chain

Every deploy kills containers. The difference between "zero-downtime deploy" and "a burst of 502s" is what happens in the next few seconds:

1. **Docker sends SIGTERM to PID 1.** This is why 11-1 insisted on **exec-form CMD** — if PID 1 is `/bin/sh`, the signal dies there and uvicorn never hears it.
2. **uvicorn stops accepting** new connections (the load balancer / compose routes elsewhere).
3. **In-flight requests drain** — up to `--timeout-graceful-shutdown 30` seconds.
4. **Lifespan shutdown runs** — your lifespan's cleanup closes the SQLAlchemy engine and the Redis pool, so nothing is dropped mid-write.
5. Process exits 0. If it hasn't within `stop_grace_period`, Docker sends SIGKILL — which is why the grace period must **exceed** the drain timeout.

> **Tip — the whole chain has one weakest link.** Shell-form CMD, a missing `stop_grace_period`, or a drain timeout longer than the grace period each silently turn "graceful" into SIGKILL. The gate's part (b) makes you prove the chain end to end.

---

## /healthz vs /readyz

Two questions, two endpoints, deliberately different answers:

- **Liveness (`/healthz`): "is the process up?"** Failing it means *restart me*. It must **not** check dependencies — if Postgres blips and every replica's liveness fails, the orchestrator restarts your entire healthy fleet, turning a DB hiccup into a full outage. Cascading restarts are self-inflicted.
- **Readiness (`/readyz`): "can I serve real traffic?"** Failing it means *don't route to me yet* — the process keeps running and rejoins when deps recover. This one **does** check Postgres and Redis.

```python
# app/api/health.py
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.redis import get_redis      # the pool opened in lifespan (Section 09)
from app.db.session import engine

router = APIRouter()


@router.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    # Liveness: reaching this line proves the process and event loop are alive.
    # NO dependency checks here — see cascading-restart note above.
    return {"status": "ok"}


@router.get("/readyz", include_in_schema=False)
async def readyz(response: Response) -> dict[str, str]:
    # Readiness: cheap, real checks against every hard dependency.
    checks: dict[str, str] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))    # full round-trip through the pool
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "unavailable"

    try:
        await get_redis().ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    if any(v != "ok" for v in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return checks
```

The Dockerfile `HEALTHCHECK` from 11-1 probes `/healthz`; a load balancer or k8s readiness probe targets `/readyz`. Bring it all up and verify:

```bash
cp .env.example .env               # set a real POSTGRES_PASSWORD
docker compose up -d --build
docker compose ps                  # migrate → Exited (0); api/worker → Up (healthy)
curl -s localhost:8000/readyz      # {"postgres":"ok","redis":"ok"}
docker compose stop postgres && curl -si localhost:8000/readyz | head -1   # HTTP/1.1 503
docker compose start postgres
```

---

## Recap & next

- ✅ Compose runs the full stack; startup order is enforced by **healthchecks + `depends_on` conditions**, with migrate gated on `service_completed_successfully`.
- ✅ **Migrations are a deploy step, never app startup** — N replicas racing DDL is a deploy-time outage. Migrate, then roll.
- ✅ Config and secrets enter at **runtime** via env; the image stays config-free; `.env` never leaves your machine.
- ✅ **Graceful shutdown chain:** SIGTERM → stop accepting → drain (`--timeout-graceful-shutdown`) → lifespan cleanup — and exec-form CMD + `stop_grace_period` keep every link intact.
- ✅ **`/healthz` = restart me** (never checks deps); **`/readyz` = don't route to me** (SELECT 1 + PING, 503 on failure).
- ✅ Self-check: your DB has a 30-second blip at peak traffic. Walk through what happens to a fleet whose *liveness* probe checks the DB, versus one where only *readiness* does.

→ Next: **[11-3 · CI/CD with GitHub Actions](03_cicd_github_actions.md)**

## Exercises

1. Comment out the two `condition:` lines under the api's `depends_on`, then `docker compose down && docker compose up`. What failure do you see, and why is it timing-dependent?

<details>
<summary>Solution</summary>

Bare `depends_on` only orders container *start*, not readiness — the api boots while Postgres is still initializing and/or before migrate has run, so you get connection-refused errors or "relation does not exist" (queries against unmigrated schema). Sometimes it works, when Postgres happens to win the race — which is exactly what makes it a terrible bug class. The `service_healthy` / `service_completed_successfully` conditions replace luck with a contract.
</details>

2. Prove the migration race to yourself: describe (or try, with `docker compose up --scale api=3` and migrations moved into the lifespan) what three replicas running `alembic upgrade head` simultaneously do to a deploy. Why doesn't Alembic's internal locking fully save you?

<details>
<summary>Solution</summary>

All three replicas hit the DB with the same DDL at once. Alembic's version-table locking means one wins — but the others block on the lock, hit statement/startup timeouts, and crash-loop; on some backends partial DDL isn't transactional, so an interrupted loser can leave a half-applied state. Even in the happy case, your app's startup time now includes someone else's migration. The lock prevents corruption at best; it doesn't make startup-migrations a sane deploy mechanism. One gated migrate step has none of these failure modes.
</details>

3. Run the readiness flip: `docker compose stop redis`, then hit `/healthz` and `/readyz`. Explain each response, and what an orchestrator would do with them.

<details>
<summary>Solution</summary>

`/healthz` still returns 200 — the process is fine, so no restart (correct: restarting won't fix Redis). `/readyz` returns 503 with `"redis": "unavailable"` — an orchestrator/LB pulls the replica out of rotation but leaves it running. When `docker compose start redis` brings Redis back, `/readyz` flips to 200 and traffic returns, with zero restarts anywhere. That asymmetry is the entire point of having two endpoints.
</details>
