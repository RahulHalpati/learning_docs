# 99 · Capstone — the linkstash pipeline

A small Flask app (`linkstash`, a link shortener) wrapped in a complete, gated
CI/CD pipeline. The app is tiny on purpose; the pipeline is the deliverable.

```
push/PR → lint → test(3.10/3.11/3.12) → security → build image → GHCR
        → deploy staging → smoke → approve → deploy production → smoke
tag v* → versioned image + GitHub Release
```

---

## Layout

```
99_project_cicd_pipeline/
├── app/
│   ├── core.py            # pure logic (URL validation, slug) — unit-tested
│   └── main.py            # Flask: /health, /shorten, /<slug>
├── tests/                 # test_core.py (unit) + test_api.py (integration)
├── Makefile               # local mirror of every CI stage (make ci)
├── Dockerfile             # multi-stage, non-root image
├── .dockerignore
├── pyproject.toml         # ruff + pytest + coverage config, package metadata
├── requirements.txt       # runtime (flask)
├── requirements-dev.txt   # ruff, pytest, coverage, bandit, pip-audit
├── scripts/
│   ├── deploy.sh          # mock deploy (replace with your platform)
│   └── smoke_test.sh      # post-deploy health + core-flow check
└── .github/workflows/
    ├── ci.yml             # lint · test matrix · security (SAST+SCA)
    ├── cd.yml             # build→GHCR · staging · approval · production
    └── release.yml        # tag v* → versioned image + GitHub Release
```

---

## Quick start (local, offline)

```bash
make install          # venv + dev tooling
make ci               # lint + coverage + security — the exact CI stages
make build            # docker image
make run              # run the app at http://127.0.0.1:8000
make smoke            # hit /health on the running app
```

### Verified output (2026-07-16)

```
$ make ci
All checks passed!                     # ruff
8 passed in 0.16s                       # pytest
app/core.py   21   0  100%
app/main.py   29   1   97%
TOTAL         51   1   98%              # coverage gate ≥80%
No known vulnerabilities found          # pip-audit
✅ CI passed locally

$ docker build -t linkstash:local .     # → build succeeded
$ docker run -d -p 8011:8000 linkstash:local
$ ./scripts/smoke_test.sh http://127.0.0.1:8011
✅ smoke test passed
```

---

## Make targets ↔ pipeline stages

| `make` | Stage | Tool |
|---|---|---|
| `lint` | style + bugs | ruff |
| `test` / `cov` | tests + coverage gate | pytest, coverage |
| `security` | SAST + SCA | bandit, pip-audit |
| `build` | container image | Docker |
| `smoke` | post-deploy check | curl |
| `ci` | lint + cov + security | (all) |

The workflows in `.github/workflows/` run these same commands on GitHub's runners.

---

## To run it on GitHub

1. Push this project to a repo.
2. **Settings → Environments**: create `staging` and `production`; add a
   **required reviewer** to `production`; set `STAGING_URL` / `PRODUCTION_URL` vars.
3. **Settings → Branches**: protect `main`, require the CI checks.
4. Open a PR → CI runs. Merge → CD builds, deploys staging, waits for your
   approval, then production.
5. `git tag v1.2.1 && git push --tags` → a release.

`deploy.sh` is a mock (it prints what it would do) — swap in your platform's
command (kubectl / fly / ECS / ssh). Everything else is real.

---

## What it reuses from other courses

- **[Docker](../../docker/)** — the multi-stage image pattern.
- **[Secure Code Audit](../../secure_code_audit/)** — bandit (SAST) + pip-audit
  (SCA) as the security stage; drop in your own `codeaudit` tool too.
- **OpenTofu** (next course) — provisions the environment `deploy.sh` targets.

→ Course starts at the **[README](../README.md)** → **[00 · Introduction](../00_introduction.md)**.
