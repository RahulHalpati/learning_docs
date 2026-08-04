# 99 · Capstone — TaskFlow

> **Level:** Intermediate → Advanced · **Prerequisites:** Sections 01–09
> **Time:** the whole course · **Verified:** 2026-07-27 · Python 3.10 · fastapi 0.140.8 · SQLAlchemy 2.0.51 · alembic 1.18.5 · PyJWT 2.13.0 · asyncpg 0.31.0 · redis 5.3.1 · arq 0.28.0

The complete, runnable, tested service the whole course builds — a **task & project management API** with every production concern wired in. This is the reference implementation each lesson teaches a slice of.

## What's in it

| Layer / concern | Where |
|-----------------|-------|
| Layered architecture (api → services → repositories → models) | `app/` |
| Async SQLAlchemy 2.0 models + relationships | `app/models/` |
| Alembic migrations | `migrations/` |
| Pydantic schemas + pagination | `app/schemas/` |
| Repository + service pattern | `app/repositories/`, `app/services/` |
| JWT/OAuth2 auth, hashing, roles, ownership | `app/core/security.py`, `app/api/deps.py`, `app/services/auth.py` |
| Versioned routers, error handling | `app/api/v1/`, `app/core/exceptions.py` |
| Redis cache + rate limiting, arq jobs | `app/integrations/`, `worker.py` |
| Structured logging, metrics, health probes | `app/observability/`, `app/api/v1/health.py` |
| Tests (pytest + httpx + test DB) | `tests/` |
| Docker, docker-compose, Makefile | `Dockerfile`, `docker-compose.yml`, `Makefile` |

## The API

```
POST   /api/v1/auth/register            create an account
POST   /api/v1/auth/login               OAuth2 login -> access + refresh tokens
POST   /api/v1/auth/refresh             new access token from a refresh token
GET    /api/v1/auth/me                  current user (protected)

GET    /api/v1/projects                 list my projects (paginated)
POST   /api/v1/projects                 create a project
GET    /api/v1/projects/{id}            get one (owner/admin only)
PATCH  /api/v1/projects/{id}            update
DELETE /api/v1/projects/{id}            delete

GET    /api/v1/projects/{id}/tasks      list tasks (?status=, paginated)
POST   /api/v1/projects/{id}/tasks      create a task
GET/PATCH/DELETE  .../tasks/{task_id}   task CRUD

GET    /api/v1/healthz  /readyz         liveness / readiness
GET    /metrics                         Prometheus metrics
```

## Run it (offline, SQLite, no setup)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head            # create the schema
uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
```

Explore the interactive docs at `/docs`, click **Authorize**, and try the endpoints.

## Test it

```bash
pytest -q
```

**Output (real run):**
```
.............                                                            [100%]
13 passed in 3.90s
```

Covers the auth flow, project/task CRUD, pagination, status filtering, **ownership isolation** (user B can't touch user A's data), health probes, and the Redis integrations (which skip if no Redis). All offline on SQLite.

## Run the full stack (Postgres + Redis + worker)

```bash
docker compose up --build       # API + Postgres + Redis + arq worker
# → http://localhost:8000/docs
docker compose down -v
```

The API container **applies migrations on boot** then serves — verified end to end:

**Output (real run, container):**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0576dd2868d7, initial schema
INFO:     Application startup complete.
GET /api/v1/healthz  ->  {"status":"ok"}
GET /api/v1/readyz   ->  {"status":"ready","database":"ok"}
```

Switch to Postgres locally by setting `DATABASE_URL=postgresql+asyncpg://…` — the app, migrations, and tests are DB-agnostic.

## Layout

```
99_project_taskflow/
├── app/
│   ├── main.py                 core/ db/ models/ schemas/
│   ├── repositories/ services/ api/v1/ integrations/ observability/
├── migrations/                 # Alembic
├── tests/                      # pytest + httpx (13 tests)
├── Dockerfile · docker-compose.yml · Makefile · alembic.ini
└── requirements.txt · .env.example
```

## Where next

- **[Docker](../../docker/)** · **[Kubernetes](../../kubernetes/)** — take this image to a real cluster.
- **[CI/CD with GitHub Actions](../../cicd_github_actions/)** — lint → test → build → deploy this app.
- **[OpenTofu / IaC](../../opentofu_iac/)** — provision its Postgres/Redis as code.
- **[FastAPI · Async · WebSockets](../../fastapi_async_websockets/)** — add real-time/streaming features and deeper Redis scaling.

## Extend it

- Add **teams/members** so projects can be shared (many-to-many) — exercises a join table and richer authorization.
- Add **file attachments** on tasks (object storage / S3).
- Wire **OpenTelemetry** tracing ([08-3](../08_observability_and_ops/03_metrics_and_tracing.md)).
- Add a **CI pipeline** that runs `pytest` and builds the image on every push.
