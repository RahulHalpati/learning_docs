# 09-2 · Docker Compose stack

> **Level:** Intermediate · **Prerequisites:** [09-1 · The Dockerfile](01_dockerfile.md)
> **Time:** 30 min · **Verified:** 2026-07-27 (Docker Compose; config validated)

## Why this matters

TaskFlow isn't just the API — it's the API **plus Postgres, Redis, and a worker**. Running four things by hand, in the right order, with the right connection strings, is tedious and error-prone. **Docker Compose** declares the whole stack in one file so `docker compose up` brings it all up, wired together, every time.

---

## The stack

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment: { POSTGRES_USER: taskflow, POSTGRES_PASSWORD: taskflow, POSTGRES_DB: taskflow }
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]        # persist data across restarts
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U taskflow"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  api:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://taskflow:taskflow@db:5432/taskflow
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET:-dev-secret-change-me-in-production-0123456789}
    ports: ["8000:8000"]
    depends_on:
      db: { condition: service_healthy }               # wait until Postgres is READY
      redis: { condition: service_started }

  worker:
    build: .
    command: arq app.integrations.tasks.WorkerSettings
    environment:
      DATABASE_URL: postgresql+asyncpg://taskflow:taskflow@db:5432/taskflow
      REDIS_URL: redis://redis:6379
    depends_on:
      redis: { condition: service_started }

volumes: { pgdata: {} }
```

```bash
docker compose up --build      # build the image, start db + redis + api + worker
docker compose down -v         # stop and remove (incl. the data volume)
```

**Output (real run, `docker compose config`):**
```
compose config valid ✅
```

---

## The four ideas that make it a *stack*

- **Service-name networking.** The API reaches Postgres at `db:5432` and Redis at `redis:6379` — Compose gives each service a DNS name. No IPs, no `localhost` (which inside a container means the container itself).
- **`depends_on` with `condition: service_healthy`.** The API waits until Postgres's healthcheck passes — not merely "started". This avoids the classic "app boots before the DB accepts connections and crashes" race. (Postgres's own `healthcheck` is what makes this possible.)
- **The worker is its own service.** Same image, different command (`arq ...`), scaled independently — burst workers without touching the API.
- **A named volume (`pgdata`)** persists the database across `up`/`down` (until you `down -v`). Containers are ephemeral; the volume is where state lives.

> **Tip — env & secrets.** `JWT_SECRET: ${JWT_SECRET:-<dev default>}` reads from your shell/`.env`, falling back to a dev value. In real deploys, inject secrets from your platform (Kubernetes Secrets, cloud Secret Manager) — never hard-code them in the compose file or image.

---

## Compose is for local; orchestrators for prod

Compose is ideal for **local dev and CI** — the whole stack on one command. For **production**, the same image goes to Kubernetes ([Kubernetes course](../../kubernetes/)), Cloud Run, or ECS, where the DB and Redis are usually *managed* services (RDS/ElastiCache) rather than containers. The app doesn't change — only where its dependencies live, set via `DATABASE_URL`/`REDIS_URL`.

---

## Recap & next

- ✅ Compose declares the whole stack (API + Postgres + Redis + worker); `up` starts it wired together.
- ✅ Services reach each other by **name** (`db`, `redis`); `depends_on: service_healthy` fixes boot-order races.
- ✅ The **worker** is a separate service (same image, `arq` command); a **volume** persists the DB.
- ✅ Compose for local/CI; the same image runs on an orchestrator with managed DB/Redis in prod.
- ✅ Self-check: why does the API connect to `db:5432` and not `localhost:5432` inside the container?

→ Next: **[09-3 · Deployment checklist](03_deployment_checklist.md)**

## Exercises

1. Add a second `api` replica on port 8001 (same DB/Redis) and confirm both serve — the horizontal-scaling shape.

<details>
<summary>Solution</summary>

Duplicate the `api` service as `api2` with `ports: ["8001:8000"]`, same env. Both share the one Postgres and Redis; requests to either work. That's exactly how you scale in production — more replicas behind a load balancer, shared stateful backends.
</details>
