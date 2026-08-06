# 09-2 · Docker & compose

> **Level:** Intermediate · **Prerequisites:** [09-1 · Gunicorn & WSGI](01_gunicorn_wsgi.md)
> **Time:** 40 min · **Verified:** 2026-07-29 (`docker compose config` validates)

## Why this matters

A container packages your app *and* its exact dependencies into one artifact that runs identically on your laptop, in CI, and in production. For Flask it also solves a real problem: making sure migrations run **before** the new code serves traffic.

> For Docker from first principles, see the [Docker course](../../docker/). This is the Flask-specific recipe.

---

## The Dockerfile

```dockerfile
# Multi-stage: build deps separately so the final image stays small.
FROM python:3.10-slim AS builder
WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY --from=builder /install/deps /usr/local        # only the packages, no build tools
COPY app ./app
COPY migrations ./migrations
COPY wsgi.py .

RUN useradd --create-home appuser && chown -R appuser /srv
USER appuser                                         # never run as root

EXPOSE 8000
CMD ["sh", "-c", "flask db upgrade && gunicorn -w 4 -b 0.0.0.0:8000 'wsgi:app'"]
```

Each choice earns its place:

- **Multi-stage** — the builder installs; the final image copies only the installed packages. Smaller image, no compilers shipped to production.
- **`PYTHONUNBUFFERED=1`** — logs reach stdout immediately so your platform can collect them ([07-2](../07_errors_logging_cors/02_logging.md)).
- **Non-root `appuser`** — if the app is compromised, the attacker isn't root inside the container.
- **`flask db upgrade && gunicorn ...`** — the schema is always current before the app serves. This is the Flask deployment detail people forget.

Add a `.dockerignore` (`.venv`, `__pycache__`, `.git`, `*.db`, `tests/`) so the build context stays small and no local database is baked into the image.

---

## The full stack with compose

```yaml
services:
  web:
    build: .
    ports: ["8000:8000"]
    environment:
      FLASK_ENV: production
      SECRET_KEY: ${SECRET_KEY:-change-me-in-production-please-32-chars}
      DATABASE_URL: postgresql+psycopg://flask:flask@db:5432/flasknotes
    depends_on:
      db: {condition: service_healthy}       # wait until Postgres actually accepts connections
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: flask
      POSTGRES_PASSWORD: flask
      POSTGRES_DB: flasknotes
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flask"]
      interval: 5s
      retries: 5
volumes: { pgdata: {} }
```

```bash
docker compose up --build      # app + Postgres, wired together
docker compose down -v         # tear it down (and drop the data volume)
```

**Output (real run):**
```
docker compose config  ->  valid ✅
```

The four ideas that make it a *stack*:

- **Service-name networking** — the app reaches Postgres at `db:5432`, not `localhost` (which inside a container means the container itself).
- **`condition: service_healthy`** — the app waits for a DB that's *ready*, not merely *started*. This fixes the classic "app boots, crashes because Postgres isn't accepting connections yet" race.
- **A named volume** — containers are disposable; `pgdata` is where the data actually lives.
- **Config via environment** — the same image runs in every environment ([04-3](../04_app_structure/03_config_and_env.md)).

> ⚠️ **Don't commit real secrets in compose.** `${SECRET_KEY:-default}` reads from your shell or `.env`; in production inject secrets from your platform's secret store. And change the Postgres password — `flask/flask` is fine for local only.

---

## Uploads need a volume

FlaskNotes writes uploaded images to disk. Container filesystems are **ephemeral** — a redeploy wipes them. Either mount a volume:

```yaml
    volumes: ["uploads:/srv/app/uploads"]
```

…or (better at scale) store objects in S3-compatible storage, since local disk doesn't survive multiple replicas either.

---

## Recap & next

- ✅ **Multi-stage** build, **non-root** user, `PYTHONUNBUFFERED=1`, `.dockerignore`.
- ✅ `CMD` runs **`flask db upgrade` then gunicorn** — schema current before serving.
- ✅ Compose wires app + Postgres by **service name**, gated on a **healthcheck**, with a named volume.
- ✅ Uploads need a volume (or object storage) — container disk is ephemeral.
- ✅ Self-check: why does the app connect to `db:5432` instead of `localhost:5432`?

→ Next: **[09-3 · Production checklist](03_production_checklist.md)**

## Exercises

1. Add an `uploads` volume to the `web` service and confirm an uploaded image survives `docker compose restart web`.

<details>
<summary>Solution</summary>

Declare `uploads: {}` under `volumes:` and mount it at `/srv/app/uploads`. Upload an image, `docker compose restart web`, reload the page — the image is still there. Without the volume it's gone, which is the lesson.
</details>
