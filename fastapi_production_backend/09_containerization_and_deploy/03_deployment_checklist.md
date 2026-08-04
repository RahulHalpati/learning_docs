# 09-3 · Deployment checklist

> **Level:** Intermediate · **Prerequisites:** [09-2 · Docker Compose stack](02_docker_compose.md)
> **Time:** 25 min · **Verified:** 2026-07-27 (synthesis of the course)

## Why this matters

"It runs locally" and "it's ready for production" are far apart. This lesson is the concrete checklist that closes the gap — the things that, if skipped, become the 2am incident. Everything here was built earlier in the course; this pulls it together into a go/no-go list.

---

## The checklist

### Security
- ☐ **`JWT_SECRET` is a long random value from the environment** — not the dev default, not in git ([01-2](../01_foundations_and_structure/02_config_and_settings.md)).
- ☐ **Passwords hashed** with bcrypt/argon2; no plaintext anywhere ([04-1](../04_auth_and_security/01_password_hashing.md)).
- ☐ **CORS `allow_origins`** lists real frontend origins, not `*` ([05-3](../05_api_design_and_robustness/03_middleware_and_cors.md)).
- ☐ **Container runs as non-root** ([09-1](01_dockerfile.md)); no secrets baked into the image.
- ☐ **Rate limiting** on auth endpoints ([07-2](../07_integrations/02_rate_limiting.md)).
- ☐ Error responses **leak no internals** (safe messages, no stack traces) ([05-2](../05_api_design_and_robustness/02_error_handling.md)).

### Data
- ☐ **Postgres**, not SQLite; `DATABASE_URL` points at the managed DB.
- ☐ **Migrations run on deploy** (`alembic upgrade head`); in multi-replica, as a one-shot step, not racing replicas.
- ☐ **Backups** configured on the database.
- ☐ Connection **pool sized** for your worker/replica count.

### Reliability & ops
- ☐ **Liveness & readiness** probes wired to the orchestrator ([08-2](../08_observability_and_ops/02_health_checks.md)).
- ☐ **Structured logs** to stdout; a request id on every line ([08-1](../08_observability_and_ops/01_structured_logging.md)).
- ☐ **Metrics** scraped; alerts on error rate & p95 latency ([08-3](../08_observability_and_ops/03_metrics_and_tracing.md)).
- ☐ **Tests pass in CI** on every push ([06](../06_testing/README.md)); image built and scanned.
- ☐ **Resource limits** (CPU/memory) set; autoscaling policy defined.
- ☐ A **rollback** plan (previous image tag) and migrations that are backward-compatible for zero-downtime deploys.

### Config
- ☐ **Everything via env vars** — one image, per-environment config ([01-2](../01_foundations_and_structure/02_config_and_settings.md)).
- ☐ **Secrets from a secret manager**, never the repo or image.
- ☐ `ENVIRONMENT=production`, `DEBUG=false`.

> ⚠️ **The top three that bite hardest:** a **default/committed `JWT_SECRET`** (total auth bypass), **`CORS=*`** (any site can call your API), and **no migration step** (app boots against an old schema and errors). Verify these three first, every time.

---

## Zero-downtime deploys (the idea)

To deploy without an outage:
1. Make migrations **backward-compatible** — the old and new code must both work against the new schema (add columns before using them; drop them a release later). Never rename in one step.
2. Run migrations, then **roll out** new replicas gradually (readiness gates traffic to ready ones).
3. Keep the previous image tag ready for an instant **rollback**.

Expand-then-contract migrations + gradual rollout + readiness probes = deploys users never notice.

---

## Where to run it

| Target | Good for | Notes |
|--------|----------|-------|
| **Cloud Run / App Runner** | most services | serverless containers, scale-to-zero, minimal ops |
| **Kubernetes** | scale / existing k8s | probes + HPA map to what we built ([K8s course](../../kubernetes/)) |
| **A VM + compose** | small/simple | cheapest; you own the ops |

The **same image** runs on all of them — that's the payoff of containerizing.

---

## Recap & next

- ✅ Production-readiness is a **checklist**, not a vibe: security, data, reliability, config.
- ✅ The three deadliest misses: committed `JWT_SECRET`, `CORS=*`, no migration step.
- ✅ Zero-downtime = backward-compatible (expand/contract) migrations + gradual rollout + readiness + rollback.
- ✅ The one image deploys to Cloud Run / Kubernetes / a VM alike.
- ✅ Self-check: name the three checklist items you'd verify *first* before any production deploy.

→ Next: **[99 · Capstone: TaskFlow](../99_project_taskflow/README.md)**

## Exercises

1. Run the checklist against the TaskFlow capstone as-shipped. Which items are done, and which are "your job at deploy time" (e.g. real secret, real CORS origins, backups)?

<details>
<summary>Solution</summary>

Done in the repo: hashing, non-root container, migrate-on-boot, probes, structured logs, metrics, tests, error hygiene, env-driven config. Your-job-at-deploy: set a real `JWT_SECRET`, real `CORS_ORIGINS`, point at managed Postgres, configure backups/limits/alerts. The code is production-*shaped*; deployment supplies the environment specifics.
</details>
