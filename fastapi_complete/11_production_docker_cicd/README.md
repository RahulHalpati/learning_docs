# Section 11 · Production: Docker, CI/CD & deployment

> **Prerequisites:** [10 · Robustness & observability](../10_robustness_observability/README.md) · **Time:** ~6 h

Everything so far ran on your machine. This section makes it ship: package the app as a small, non-root **Docker** image built with uv, run the full stack — API, worker, Postgres, Redis, a gated migration step — with **docker compose**, and put **GitHub Actions** in front of every push so nothing broken ever reaches `main`. By the end, `docker compose up` from a clean clone is a working production-shaped system.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 11-1 | [Docker: multi-stage builds with uv](01_docker_multistage.md) | How do I package the app as a small, secure, reproducible image? |
| 11-2 | [Compose & runtime](02_compose_and_runtime.md) | How do I run the full stack — and deploy/shut down without dropping requests? |
| 11-3 | [CI/CD with GitHub Actions](03_cicd_github_actions.md) | How does every push prove itself before an image is published? |
| 11-4 | [Gunicorn: process manager & worker model](04_gunicorn_workers.md) | How do I run FastAPI under Gunicorn+Uvicorn workers behind Nginx — and size the workers? |

## Mini-project

**Ship the linkbox app.** Take the linkbox service you've built through this course and make it deployable:

- [ ] **Multi-stage `Dockerfile`** using uv: builder stage runs `uv sync --frozen --no-dev`, runtime stage is `python:3.12-slim` with only `.venv` + source copied in. Final image **< 300 MB**, runs as a **non-root user**, has a `HEALTHCHECK`.
- [ ] **`.dockerignore`** excluding at minimum `.venv`, `.git`, `.env`, `tests/`, caches.
- [ ] **`docker-compose.yml`** with five services: `api`, `worker` (arq, same image, different command), `postgres:16-alpine` (named volume), `redis:7-alpine`, and a one-shot `migrate` service that runs `alembic upgrade head` before the api starts.
- [ ] **Healthchecks everywhere:** Postgres via `pg_isready`, Redis via `redis-cli ping`, and `depends_on` with `condition: service_healthy` / `condition: service_completed_successfully` so startup order is enforced by health, not hope.
- [ ] **`/healthz` and `/readyz` endpoints:** liveness returns 200 unconditionally when the process is up; readiness runs `SELECT 1` against Postgres and `PING` against Redis, returning 503 if either fails.
- [ ] **Clean-clone test:** `git clone … && cp .env.example .env && docker compose up` produces a fully working stack — API answering, worker consuming jobs, migrations applied.
- [ ] **GitHub Actions workflow:** `lint` (ruff check + format --check, mypy) → `test` (Postgres + Redis service containers, `alembic upgrade head`, `pytest --cov --cov-fail-under=80`) → `build` (buildx, push to GHCR with `docker/metadata-action` tags, only on `main`) — ordered with `needs:`.

## Test task (gate)

**Production-readiness drill.** Before the capstone, prove the stack survives the three things production will do to it. Passing = **all three parts documented with the actual command transcripts** (copy-paste your terminal, don't paraphrase).

**(a) Chaos — kill the worker, lose nothing.**
Arq's queue lives in Redis, not in the worker process — prove it:

```bash
docker compose kill worker                    # worker dies mid-flight
# enqueue 5 jobs while there is NO worker (e.g. POST /links triggers a fetch job)
docker compose exec redis redis-cli keys 'arq:*'   # → jobs sitting in the queue
docker compose up -d worker
docker compose logs worker                    # → all 5 jobs picked up and completed
```

Passing: the transcript shows jobs enqueued with the worker dead, visible in Redis, then processed after restart. Zero jobs lost.

**(b) Graceful shutdown — SIGTERM drains in-flight requests.**
Start a slow request, terminate the api while it's running, and show the request still completes:

```bash
curl -s "http://localhost:8000/slow?seconds=10" &   # in-flight request
docker compose kill -s SIGTERM api                  # SIGTERM only — no SIGKILL
wait                                                # curl returns 200, not a reset
docker compose logs api | tail                      # "Waiting for connections to close" → clean exit
```

Passing: the curl gets a 200 **after** SIGTERM was sent, and the api logs show a drained, clean shutdown (not code 137/SIGKILL).

**(c) Audit — the 15-point production checklist.**
Walk your own stack through every point and record evidence (a command + its output) for each:

1. Runtime image runs as a **non-root** `USER`? (`docker compose exec api whoami`)
2. **Multi-stage**: no uv, compilers, or package cache in the final image?
3. Final image **< 300 MB**? (`docker images`)
4. **`.dockerignore`** excludes `.env`, `.git`, `.venv`, `tests/`?
5. **No secrets baked into the image**? (`docker history --no-trunc` shows no passwords in any layer)
6. Secrets come from runtime env; `.env` is in `.gitignore` and an `.env.example` is committed?
7. **Migrations gated**: run as a one-shot step before the app serves, never inside app startup?
8. `/healthz` returns 200 **without touching any dependency**?
9. `/readyz` **actually** checks deps — stop Postgres and confirm it flips to 503?
10. **Exec-form `CMD`** — PID 1 inside the container is uvicorn, not a shell? (`docker compose exec api ps -p 1`)
11. Graceful shutdown configured — `--timeout-graceful-shutdown` set, compose `stop_grace_period` ≥ your slowest request?
12. Logs are **JSON on stdout** (Section 10), no log files written inside the container?
13. **Restart policies**: `unless-stopped` on api/worker, `"no"` on migrate?
14. Postgres data on a **named volume** — survives `docker compose down` (without `-v`)?
15. **Images and actions pinned** — base images by exact tag (better: digest), GitHub Actions by version?

Passing: every point answered yes with evidence, or a written justification for any deliberate deviation.

## What you'll be able to do after this section

- Write a multi-stage, uv-based Dockerfile that produces a small, non-root, healthchecked image.
- Compose a full stack (api, worker, Postgres, Redis) with health-gated startup and a migrate-before-serve deploy order.
- Explain and demonstrate graceful shutdown, liveness vs readiness, and why migrations never belong in app startup.
- Build a CI pipeline that lints, type-checks, tests against real services, and publishes images to GHCR — gated by `needs:`.
- Audit any containerized service against a production checklist and back every claim with a command.
- Run FastAPI under **Gunicorn** with Uvicorn workers behind **Nginx**, and size/tune workers (WSGI vs ASGI, sync 2N+1 vs async ~1/core, graceful reload).

→ Start: **[11-1 · Docker: multi-stage builds with uv](01_docker_multistage.md)**
