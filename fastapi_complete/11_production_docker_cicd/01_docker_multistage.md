# 11-1 · Docker: multi-stage builds with uv

> **Level:** Intermediate→Advanced · **Prerequisites:** [10 · Robustness & observability](../10_robustness_observability/README.md)
> **Time:** ~40–50 min · **Verified:** 2026-08-07 (Docker · uv · GitHub Actions)

## Why this matters

"Works on my machine" dies here. A container image is **one artifact** that runs identically on your laptop, in CI, and in production — same Python, same dependency versions, same OS libraries, isolated from whatever is installed on the host. But a naive Dockerfile ships a bloated, root-running image with your `.env` baked into a layer. This lesson builds the image you'd actually want to be paged about: small, non-root, cache-friendly, healthchecked.

---

## Why containers

- **Same artifact everywhere** — the image you test in CI is byte-for-byte the image production runs. No "prod has a different libpq" surprises.
- **Dependency isolation** — your app's Python, system libraries, and packages travel with it; the host only needs a container runtime.
- **A deployable unit** — orchestrators (compose, Kubernetes) start, stop, scale, and roll back *images*. Everything in 11-2 and 11-3 builds on this.

## Image anatomy

An image is a stack of **layers** — each Dockerfile instruction (`COPY`, `RUN`, …) adds one. Two properties drive everything in this lesson:

- **Layers are cached.** If an instruction and its inputs haven't changed, Docker reuses the layer. Order your Dockerfile so the expensive, rarely-changing work (installing dependencies) sits *above* the frequently-changing work (copying source).
- **Layers are permanent.** Deleting a file in a later layer doesn't remove it from the earlier one — `docker history` still shows it. This is why secrets must never be copied in, even "temporarily".

---

## The Dockerfile

```dockerfile
# ---------- Stage 1: builder — has uv, builds the venv ----------
# Pin the tag; ghcr.io/astral-sh/uv:latest works but isn't reproducible.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Compile .pyc at build time (faster cold start); copy instead of hardlink
# because the cache mount is a different filesystem.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# 1) Dependencies FIRST — this layer only rebuilds when the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 2) Source AFTER — editing app code never invalidates the dependency layer.
COPY app/ app/
COPY alembic.ini ./
COPY alembic/ alembic/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------- Stage 2: runtime — slim, no uv, no compilers, no cache ----------
FROM python:3.12-slim AS runtime

# Non-root user. Root in a container is a real risk, not a formality (below).
RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app

# Only the venv and the code cross the stage boundary — nothing else.
COPY --from=builder --chown=app:app /app/.venv .venv
COPY --from=builder --chown=app:app /app/app app
COPY --from=builder --chown=app:app /app/alembic.ini ./
COPY --from=builder --chown=app:app /app/alembic alembic

# Put the venv on PATH — no `uv run`, no activation needed.
# PYTHONUNBUFFERED=1: logs reach stdout immediately, not on buffer flush —
# without it, a crashing container can die with its last logs still buffered.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app
EXPOSE 8000

# slim has no curl — use the Python that's already there.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"

# Exec form (JSON array): uvicorn IS PID 1 and receives SIGTERM directly.
# Shell form would put /bin/sh at PID 1 — and sh doesn't forward signals.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **Alternative:** instead of the uv base image, stay on `python:3.12-slim` for both stages and add uv with `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`. Same result; the uv image variant just saves a line.

`alembic.ini` and `alembic/` ride along because in 11-2 the *same image* runs `alembic upgrade head` as a one-shot migrate service — one artifact, several commands.

---

## Why multi-stage

The builder stage contains uv, its cache, and (for packages with C extensions) compiler toolchains. None of that is needed to *run* the app, so none of it crosses into the runtime stage:

- **Smaller image** — only `python:3.12-slim` + `.venv` + your code. Faster pulls, faster deploys, cheaper registry storage. Ours lands well under the 300 MB budget; check with `docker images`.
- **Smaller attack surface** — no compilers, no package installer, no build cache in production. An attacker who gets code execution in the container finds fewer tools to pivot with.

`uv sync --frozen --no-dev` is doing two production jobs: `--frozen` refuses to run if `uv.lock` is out of date (the image is exactly what you tested, or the build fails), and `--no-dev` keeps pytest/ruff/mypy out of the runtime image.

---

## Layer-caching discipline

The two-step copy is the single highest-leverage line ordering in the file:

```dockerfile
COPY pyproject.toml uv.lock ./     # changes rarely
RUN uv sync --frozen --no-dev --no-install-project   # expensive — cached
COPY app/ app/                     # changes constantly
RUN uv sync --frozen --no-dev      # cheap — just installs your project
```

If you copied the whole source tree first, *every* code edit would invalidate the copy layer and force a full dependency reinstall. With this order, editing a route rebuilds in seconds: the dependency layer is untouched until `uv.lock` itself changes. `--no-install-project` makes the first sync install only third-party dependencies (your own package isn't copied in yet); the second sync after `COPY app/` installs your project into the venv. The `--mount=type=cache` keeps uv's download cache across builds without it ever becoming an image layer.

---

## Non-root, and why it matters

By default containers run as **root**. Container isolation is good, not absolute: a kernel vulnerability, a misconfigured bind mount (`-v /:/host` and root owns your host filesystem), or an over-privileged Docker socket turns root-in-container into root-ish-on-host. Running as a dedicated `app` user costs two lines and means a compromised process can't install packages, rewrite the app, or exploit most escape paths. It's defense in depth — the cheapest kind.

---

## .dockerignore

The build context is everything Docker *could* copy. Exclude what must never enter an image:

```
# .dockerignore
.venv/          # host venv — wrong platform, huge, rebuilt in the image anyway
.git/           # full history: big, and old commits may contain secrets
.env            # SECRETS. A COPY'd .env lives in a layer forever —
.env.*          # `docker history` exposes it to anyone who can pull the image
tests/          # not needed at runtime
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
htmlcov/
```

`.env` is the one that ends careers: `COPY . .` without a `.dockerignore` bakes your database password into a layer, and pushing that image publishes it. Layers are permanent — a later `RM` doesn't unpublish anything. Config enters containers at **runtime** (11-2), never at build time.

---

## HEALTHCHECK

The `HEALTHCHECK` hits `/healthz` (built in 11-2) every 30 s. Docker marks the container `healthy`/`unhealthy`, which compose uses to gate dependent services and restart policies use to recover. `--start-period=10s` gives the app time to boot before failures count. One caveat worth knowing: **Kubernetes ignores Dockerfile HEALTHCHECKs** entirely and uses its own liveness/readiness probes — but the endpoint you're probing is the same either way.

Build and verify:

```bash
docker build -t linkbox .
docker images linkbox            # size — should be well under 300 MB
docker run --rm -p 8000:8000 --env-file .env linkbox   # env at RUNTIME
docker ps                        # STATUS column → (healthy) after ~10 s
```

---

## Recap & next

- ✅ One image = one artifact that runs identically on laptop, CI, and prod.
- ✅ **Multi-stage**: uv builds `.venv` in a builder; runtime is `python:3.12-slim` + venv + code — smaller image, smaller attack surface.
- ✅ **Copy lockfiles → sync → copy source**: dependency layer survives code edits; `--frozen` guarantees lockfile fidelity.
- ✅ **Non-root USER**, **`.dockerignore`** (especially `.env` — layers are forever), `PYTHONUNBUFFERED=1`, **exec-form CMD**, `HEALTHCHECK`.
- ✅ Self-check: why does `COPY pyproject.toml uv.lock ./` come *before* `COPY app/ app/`, and what happens to build times if you swap them?

→ Next: **[11-2 · Compose & runtime](02_compose_and_runtime.md)**

## Exercises

1. Break the cache on purpose: build once, `touch app/main.py`, build again and read the output — which steps say `CACHED`? Now move `COPY app/ app/` above the first `uv sync` and repeat. What changed?

<details>
<summary>Solution</summary>

With the correct order, the second build shows `CACHED` for the lockfile copy and the dependency sync — only the source copy and the final (cheap) sync re-run; the rebuild takes seconds. With `COPY app/ app/` first, the code change invalidates that layer and *everything after it*, so the full dependency install re-runs on every edit. Cache invalidation flows downward: put volatile inputs as low as possible.
</details>

2. Prove the secret leak: temporarily remove `.env` from `.dockerignore`, add `COPY .env .env` to the Dockerfile, build, then run `docker history --no-trunc <image>` and `docker run --rm <image> cat .env`. Then explain why deleting the file in a later `RUN rm .env` layer would *not* fix it. (Revert everything after.)

<details>
<summary>Solution</summary>

`docker history` shows the `COPY .env .env` instruction, and `cat .env` prints your secrets — anyone who can pull the image has them. A later `RUN rm .env` only masks the file in the final filesystem view; the layer created by `COPY` still contains it and can be extracted with `docker save` + untar. The only fix is never copying it: `.dockerignore` plus runtime env injection.
</details>

3. Change the `CMD` to shell form — `CMD uvicorn app.main:app --host 0.0.0.0 --port 8000` — run the container, then `docker stop` it and time how long it takes. Compare with exec form. What's happening?

<details>
<summary>Solution</summary>

Shell form takes ~10 s (Docker's default grace period): PID 1 is `/bin/sh -c`, which doesn't forward SIGTERM to uvicorn, so uvicorn never hears the stop request and Docker eventually SIGKILLs the container — killing in-flight requests with it. Exec form stops in well under a second (when idle) because uvicorn is PID 1 and handles SIGTERM by draining and exiting. This is why graceful shutdown (11-2) *requires* exec form.
</details>
