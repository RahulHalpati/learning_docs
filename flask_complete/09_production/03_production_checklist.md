# 09-3 · Production checklist

> **Level:** Intermediate · **Prerequisites:** [09-2 · Docker & compose](02_docker_deploy.md)
> **Time:** 30 min · **Verified:** 2026-07-29 (synthesis of the course)

## Why this matters

"It works locally" and "it's ready for production" are far apart, and the gap is made of small things — a debug flag, a default secret, a missing migration step. Everything here was built earlier in the course; this is the go/no-go list.

---

## The checklist

### Security
- ☐ **`DEBUG=False`.** Debug mode exposes an interactive console — remote code execution for anyone who triggers an error ([04-3](../04_app_structure/03_config_and_env.md)).
- ☐ **A real `SECRET_KEY`** from the environment, ≥32 random bytes, never in git. It signs sessions — leaking it means forgeable logins ([06-1](../06_auth_and_sessions/01_sessions_cookies.md)).
- ☐ **Passwords hashed** with scrypt/bcrypt/argon2 ([06-2](../06_auth_and_sessions/02_passwords_login.md)).
- ☐ **Cookie flags**: `SESSION_COOKIE_SECURE=True`, `HTTPONLY=True`, `SAMESITE="Lax"`.
- ☐ **HTTPS everywhere**, with `ProxyFix` configured if behind a proxy ([09-1](01_gunicorn_wsgi.md)).
- ☐ **CORS** lists real origins, never `*` ([07-3](../07_errors_logging_cors/03_cors_and_middleware.md)).
- ☐ **Uploads** validated (type + `MAX_CONTENT_LENGTH`) and stored under generated names ([03-3](../03_request_handling/03_forms_files_images.md)).
- ☐ **Errors leak nothing** — generic 500s, details only in logs ([07-1](../07_errors_logging_cors/01_error_handling.md)).
- ☐ **No `|safe`** on user-supplied content ([02-1](../02_templates_and_static/01_jinja_templates.md)).

### Data
- ☐ **Postgres, not SQLite**, via `DATABASE_URL`.
- ☐ **Migrations run on deploy** (`flask db upgrade`), as a one-off job for multi-replica.
- ☐ **Backups** configured and *restore-tested*.

### Serving & reliability
- ☐ **gunicorn**, never `flask run`; workers ≈ `(2 × cores) + 1`.
- ☐ **No state in module-level variables** — workers are separate processes.
- ☐ **Health endpoint** (`/healthz`) wired to your platform's checks.
- ☐ **Logs to stdout**, no secrets or PII ([07-2](../07_errors_logging_cors/02_logging.md)).
- ☐ **Tests pass in CI** on every push ([08](../08_testing/README.md)).
- ☐ **Uploads on a volume or object storage** — container disk is ephemeral.

### Config
- ☐ Everything via **environment variables**; one image per environment.
- ☐ Secrets from a secret manager, not the repo or image.
- ☐ `FLASK_ENV=production`.

> ⚠️ **The three that cause real incidents:** `DEBUG=True` in production (RCE), a **default/committed `SECRET_KEY`** (session forgery), and **no migration step** (app boots against an old schema). Verify these three first, every single deploy.

---

## Zero-downtime deploys

1. Make migrations **backward-compatible** — old and new code must both work against the new schema. Add a column in one release, use it in the next; never rename in one step (expand-then-contract).
2. Run migrations, then roll out replicas gradually; health checks gate traffic to ready instances.
3. Keep the previous image tag for an instant **rollback**.

---

## Where to run it

| Target | Good for | Notes |
|--------|----------|-------|
| **Cloud Run / App Runner** | most apps | serverless containers, scale-to-zero, minimal ops |
| **Kubernetes** | scale / existing k8s | health checks + HPA map onto what you built ([K8s course](../../kubernetes/)) |
| **A VM + compose** | small/simple | cheapest; you own the ops |
| **PaaS (Render/Fly/Heroku-likes)** | fastest to ship | give it the Dockerfile and go |

The **same image** runs on all of them — that's the payoff of containerizing.

---

## What's next for the app

Beyond this course, the usual next additions: **Celery or RQ** for background jobs (email, reports), **Redis** for caching and rate limiting, **Flask-Limiter** on auth endpoints, **Sentry** for error tracking, and **flask-smorest/marshmallow** if the API grows enough to want generated OpenAPI docs.

---

## Recap & next

- ✅ Production readiness is a **checklist**: security, data, serving, config.
- ✅ The three deadliest misses: `DEBUG=True`, a default `SECRET_KEY`, no migration step.
- ✅ Zero-downtime = backward-compatible migrations + gradual rollout + rollback plan.
- ✅ One image deploys to Cloud Run, Kubernetes, a VM, or a PaaS alike.
- ✅ Self-check: name the three items you'd verify before *any* production deploy.

→ Next: **[99 · Capstone: FlaskNotes](../99_project_flasknotes/README.md)**

## Exercises

1. Run this checklist against FlaskNotes as shipped. Which items are done in the repo, and which are "your job at deploy time"?

<details>
<summary>Solution</summary>

**Done in the repo:** hashing, non-root container, migrate-on-boot, `/healthz`, stdout logging, error hygiene, upload validation, env-driven config, a production config that *refuses* to start on the default secret, 20 tests.
**Your job at deploy:** a real `SECRET_KEY`, HTTPS + `ProxyFix`, real CORS origins, managed Postgres, backups, uploads volume/S3, CI. The code is production-*shaped*; deployment supplies the environment.
</details>
