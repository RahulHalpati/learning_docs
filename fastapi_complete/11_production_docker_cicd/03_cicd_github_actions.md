# 11-3 · CI/CD with GitHub Actions

> **Level:** Intermediate→Advanced · **Prerequisites:** [11-2 · Compose & runtime](02_compose_and_runtime.md)
> **Time:** ~40–50 min · **Verified:** 2026-08-07 (Docker · uv · GitHub Actions)

## Why this matters

CI is the "works on my machine" killer: every push runs the *same* lint, type-check, and test suite on a clean machine, against real Postgres and Redis — so "it passed" means something. And because 11-1 made the image the deployable artifact, CI's last job publishes it: a green pipeline on `main` ends with a pulled-and-tested image in the registry, ready to deploy. Nothing reaches production that didn't survive this gauntlet.

---

## Workflow anatomy

A workflow is a YAML file in `.github/workflows/`, made of three nouns:

- **Triggers** (`on:`) — we run on every PR and every push to `main`.
- **Jobs** — run in parallel on fresh runners *unless* you order them with `needs:`. Ours form a pipeline: `lint → test → build`. Fail fast and cheap: a 30-second lint failure shouldn't cost a 5-minute test run, and no image gets built from failing code.
- **Steps** — commands or reusable **actions** (`uses:`) within a job.

```yaml
# .github/workflows/ci.yml
name: ci

on:
  push:
    branches: [main]
  pull_request:
```

---

## Job 1 · lint: the 30-second gate

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true            # caches uv's downloads across runs
      - run: uv sync --frozen           # dev deps included — ruff/mypy live there
      - run: uv run ruff check .
      - run: uv run ruff format --check .   # --check: fail, don't reformat — CI never mutates code
      - run: uv run mypy app
```

`uv sync --frozen` is the same command as the Dockerfile's — CI installs *exactly* the locked versions or fails, so CI, your laptop, and the image can never quietly drift apart.

---

## Job 2 · test: against real services

Unit tests with mocks lie about integration. GitHub Actions **service containers** give the job a real Postgres and Redis on `localhost`:

```yaml
  test:
    needs: lint                         # don't burn test minutes on unformatted code
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine       # same major version as production — always
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports: ["5432:5432"]
        options: >-                     # the job waits for health before steps run
          --health-cmd "pg_isready -U test"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 10
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 10
    env:
      DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test
      REDIS_URL: redis://localhost:6379/0
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run alembic upgrade head          # migrations ARE code — CI tests them too
      - run: uv run pytest --cov=app --cov-fail-under=80
```

Two deliberate choices:

- **`alembic upgrade head` before pytest** — the schema comes from your real migration chain, not `create_all()`. A migration that doesn't apply cleanly from empty → head fails CI *here*, weeks before it fails a deploy.
- **`--cov-fail-under=80`** — the coverage gate makes "we have tests" enforceable. Pick a threshold you actually meet, then ratchet it up; a gate you routinely skip teaches everyone to skip gates.

---

## Job 3 · build: publish the artifact

Only code that linted, type-checked, and passed tests gets to become an image:

```yaml
  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write                   # allows GITHUB_TOKEN to push to GHCR
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}   # auto-issued per run, scoped to this repo
      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha                                            # ghcr.io/you/linkbox:abc1234 — deployable, traceable
            type=ref,event=branch
            type=raw,value=latest,enable={{is_default_branch}}  # latest only ever points at main
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: ${{ github.ref == 'refs/heads/main' }}   # PRs prove it BUILDS; only main PUBLISHES
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha           # reuse layers from previous CI runs —
          cache-to: type=gha,mode=max    # the 11-1 layer discipline pays off here too
```

`docker/metadata-action` generates tags instead of you hand-rolling them: every image is traceable to a commit (`type=sha`), and deploys reference immutable SHA tags — `latest` is for humans, not deploy scripts.

---

## Secrets & branch protection

- **Secrets live in repo settings** (Settings → Secrets and variables → Actions), referenced as `${{ secrets.NAME }}` — **never** literal values in YAML, which is world-readable in a public repo and history-permanent in any repo. Note we needed zero custom secrets: `GITHUB_TOKEN` is issued automatically per run and scoped to the repo — prefer it over personal access tokens wherever it suffices.
- **Branch protection** makes green mean *mandatory*: protect `main`, require the `lint`, `test`, and `build` checks to pass, and require PRs. Now the pipeline isn't advice — unmergeable is unmergeable.

---

## CD, honestly

This course stops, deliberately, at **image published + the migrate-then-roll strategy from 11-2** — because that part is universal and the last mile isn't. From here, deployment is picking a target: SSH to a VM and `docker compose pull && docker compose up -d` (fine for a single box), a Kamal-style tool that automates exactly that with health-gated rollover, a Kubernetes `Deployment` with a migration Job and rolling update, or a PaaS (Fly.io, Render, Cloud Run) that pulls your GHCR image and handles the rest. Whatever the target: **run migrations as a gated step, then roll replicas onto the new image, and let `/readyz` gate the traffic** — you already know the hard part.

---

## Recap & next

- ✅ CI = same checks, clean machine, every push: `lint → test → build`, ordered with `needs:` so failures are fast and cheap.
- ✅ Tests run against **real Postgres + Redis service containers**, on a schema built by `alembic upgrade head` — CI exercises the migrations too.
- ✅ Coverage gate (`--cov-fail-under`) and **branch protection** turn quality from convention into mechanism.
- ✅ `build` pushes to **GHCR** only on `main`, tagged by `metadata-action` (SHA = deployable truth), with `gha` layer caching.
- ✅ Secrets in repo settings, never in YAML; `GITHUB_TOKEN` over PATs.
- ✅ Self-check: why does the test job run `alembic upgrade head` instead of `Base.metadata.create_all()` — what class of bug does each choice catch or miss?

→ Next: **[11-4 · Gunicorn: process manager & worker model](04_gunicorn_workers.md)**

## Exercises

1. Push a commit with a deliberate formatting violation (e.g. wrong quotes if your ruff config enforces them). Which jobs run, which are skipped, and how long did the failure take? Why is that ordering worth the sequential-pipeline cost?

<details>
<summary>Solution</summary>

`lint` fails in ~30 seconds; `test` and `build` show as *skipped* because their `needs:` chain is broken. You paid half a minute instead of the full test-plus-build run, and no image was produced from bad code. The trade-off is that a fully green run is slower than running all jobs in parallel — but failures are far more common than releases, so optimizing the failure path wins. (Teams that need both split lint/test into parallel jobs and make only `build` need both.)
</details>

2. Add a second coverage step that uploads the HTML report as a workflow artifact (`actions/upload-artifact`) — but only when the test job *fails*. Which step option do you need?

<details>
<summary>Solution</summary>

```yaml
      - run: uv run pytest --cov=app --cov-fail-under=80 --cov-report=html
      - uses: actions/upload-artifact@v4
        if: failure()                  # steps after a failed step are skipped by default
        with:
          name: coverage-html
          path: htmlcov/
```

`if: failure()` overrides the default `if: success()` on every step, so the upload runs precisely when you need to inspect what wasn't covered. (Use `if: always()` to upload on both outcomes.)
</details>

3. Your teammate proposes deploy scripts that pull `ghcr.io/you/linkbox:latest`. Give two concrete failure modes, and what to reference instead.

<details>
<summary>Solution</summary>

(1) **No rollback:** `latest` is mutable — after a bad deploy you can't redeploy "the previous latest"; it's gone. (2) **Skew:** replicas started at different times can pull *different* images that were both called `latest`, so your fleet runs mixed code and "what's in prod?" has no answer. Deploy scripts should reference the immutable SHA tag from `metadata-action` (`:abc1234`) — rollback becomes "deploy the previous SHA", and every running container is traceable to an exact commit.
</details>
