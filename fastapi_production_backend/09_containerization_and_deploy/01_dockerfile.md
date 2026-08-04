# 09-1 · The Dockerfile

> **Level:** Intermediate · **Prerequisites:** [02-3 · Migrations with Alembic](../02_data_layer/03_migrations_alembic.md)
> **Time:** 35 min · **Verified:** 2026-07-27 (Docker 29.6.1; the image builds, runs, migrates, and serves)

## Why this matters

A container packages your app *and* its exact dependencies into one artifact that runs identically on your laptop, in CI, and in production — killing "works on my machine." A *good* Dockerfile is also **small** (fast to ship) and **secure** (non-root, minimal surface). And it must handle one production reality: **run migrations before serving.**

> For Docker from first principles, see the [Docker course](../../docker/). Here we focus on a production-grade Dockerfile for this app.

---

## Multi-stage build

Build dependencies in one stage, copy only the result into a slim final image — so build tools never ship to production:

```dockerfile
FROM python:3.10-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

FROM base AS builder
WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

FROM base AS final
WORKDIR /srv
COPY --from=builder /install/deps /usr/local     # only the installed packages
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .

# Run as a NON-ROOT user (security).
RUN useradd --create-home appuser && chown -R appuser /srv
USER appuser

EXPOSE 8000
# Migrate, THEN serve.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

The design choices, each earning its keep:

- **`python:3.10-slim`** — a small base (not full `python`, not `alpine`'s compile headaches).
- **Multi-stage** — the `builder` compiles/installs; `final` copies just the packages. No pip cache, no build tools in the shipped image → smaller, less to attack.
- **`PYTHONUNBUFFERED=1`** — logs stream to stdout immediately (so your platform sees them; [08-1](../08_observability_and_ops/01_structured_logging.md)).
- **Non-root `appuser`** — if the app is compromised, the attacker isn't root in the container. A basic, important hardening.
- **`alembic upgrade head && uvicorn ...`** — migrations run on every boot *before* serving, so the schema is always current. (In multi-replica deploys, run migrations as a separate one-shot step so replicas don't race — but this is the right default.)

---

## It really builds and runs

**Output (real run):**
```
$ docker build -t taskflow .
 => naming to docker.io/library/taskflow                          done
$ docker run -d -p 8000:8000 taskflow
$ docker logs <id>
INFO  [alembic.runtime.migration] Running upgrade  -> 0576dd2868d7, initial schema
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
$ curl localhost:8000/api/v1/healthz   ->  {"status":"ok"}
$ curl localhost:8000/api/v1/readyz    ->  {"status":"ready","database":"ok"}
```

The container migrated its database and served green health checks on first boot — the whole app in one artifact.

> **Tip — `.dockerignore`.** Add one (`.venv`, `__pycache__`, `.git`, `*.db`, `tests/`) so the build context stays small and you don't bake local junk or a dev SQLite file into the image. Smaller context = faster builds.

---

## uvicorn vs gunicorn in production

`uvicorn app.main:app` runs one worker — fine for a container you scale by running *more containers* (the Kubernetes/Cloud Run model). If you want multiple workers *inside* one container, run gunicorn with the uvicorn worker class: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4`. Prefer scaling by replicas (simpler, more elastic) unless you have a reason not to.

---

## Recap & next

- ✅ **Multi-stage** build → a small final image with no build tools.
- ✅ Run as **non-root**; `PYTHONUNBUFFERED=1` for streamed logs; slim base.
- ✅ `CMD` **migrates then serves** — schema always current on boot.
- ✅ Add a `.dockerignore`; scale by replicas (or gunicorn workers inside a container).
- ✅ Self-check: why copy from a `builder` stage instead of `pip install`-ing in the final image?

→ Next: **[09-2 · Docker Compose stack](02_docker_compose.md)**

## Exercises

1. Add a `.dockerignore`, rebuild, and compare image size / build time. What did excluding `.git`, `.venv`, and `tests/` save?

<details>
<summary>Solution</summary>

A `.dockerignore` shrinks the build context sent to the daemon (no `.git` history, no local venv, no test SQLite DB), so builds are faster and the image doesn't accidentally contain dev artifacts. It's the cheapest Dockerfile improvement there is.
</details>
