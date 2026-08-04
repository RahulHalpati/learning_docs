# 08-2 · Health checks

> **Level:** Intermediate · **Prerequisites:** [02-2 · Engine & session](../02_data_layer/02_engine_and_session.md)
> **Time:** 20 min · **Verified:** 2026-07-27 (fastapi 0.140.8; from the TaskFlow app)

## Why this matters

Orchestrators (Kubernetes, load balancers, Docker) need to ask your app two questions: *are you alive?* and *are you ready for traffic?* Health-check endpoints answer them. Get these right and the platform can restart a hung process and route traffic away from one that isn't ready — automatically. Get them wrong (or missing) and outages go unnoticed.

---

## Liveness vs readiness

They're different questions with different answers:

| Probe | Question | Checks | If it fails, the orchestrator… |
|-------|----------|--------|-------------------------------|
| **Liveness** (`/healthz`) | Is the process alive? | nothing (must be cheap) | **restarts** the container |
| **Readiness** (`/readyz`) | Can it serve traffic *now*? | dependencies (DB, etc.) | **stops routing** traffic to it (no restart) |

The distinction matters: a pod that's alive but whose database is briefly unreachable should be **taken out of rotation** (readiness fails), **not killed** (liveness must still pass). Killing it wouldn't help — the DB is the problem.

---

## The endpoints

```python
# app/api/v1/health.py
from sqlalchemy import text

@router.get("/healthz")
async def liveness():
    return {"status": "ok"}                    # cheap: no dependencies

@router.get("/readyz")
async def readiness(db: DbSession):
    await db.execute(text("SELECT 1"))         # verify the database is reachable
    return {"status": "ready", "database": "ok"}
```

**Output (real run, from the containerized app):**
```
GET /api/v1/healthz  ->  {"status": "ok"}
GET /api/v1/readyz   ->  {"status": "ready", "database": "ok"}
```

- **`/healthz`** does *nothing* — it just proves the process can respond. Keep it dependency-free so a slow database doesn't cause needless restarts.
- **`/readyz`** runs `SELECT 1` to confirm the DB connection works. If the DB is down, this fails and the load balancer stops sending traffic until it recovers.

> **Tip — readiness should check what you can't serve without.** For TaskFlow that's the database. Add Redis if a feature *hard*-depends on it — but not if the app degrades gracefully without it (ours does: cache/limits are additive). Over-checking readiness makes you fragile; under-checking routes traffic to a broken pod.

---

## Wiring into an orchestrator

In Kubernetes these map directly to probes:

```yaml
livenessProbe:
  httpGet: { path: /api/v1/healthz, port: 8000 }
readinessProbe:
  httpGet: { path: /api/v1/readyz,  port: 8000 }
```

Docker Compose uses a `healthcheck:` (as our `db` service does). The orchestrator polls these and acts — restart on liveness failure, drain on readiness failure. You saw the containerized TaskFlow answer both green on boot ([09](../09_containerization_and_deploy/README.md)).

---

## Recap & next

- ✅ **Liveness** (`/healthz`) = "am I alive?" — cheap, no deps; failure → restart.
- ✅ **Readiness** (`/readyz`) = "can I serve now?" — checks the DB; failure → drain traffic, no restart.
- ✅ Check in readiness only what you truly can't serve without (DB yes; optional Redis no).
- ✅ These map straight to Kubernetes probes / compose healthchecks.
- ✅ Self-check: the database blips for 10 seconds — which probe should fail, and why not the other?

→ Next: **[08-3 · Metrics & tracing](03_metrics_and_tracing.md)**

## Exercises

1. Add an optional Redis check to `/readyz` that reports `redis: "ok"|"down"` but does **not** fail readiness (since the app degrades gracefully without Redis).

<details>
<summary>Solution</summary>

`try: await get_redis().ping(); redis="ok"` / `except: redis="down"`, include it in the response but keep the 200. Readiness still gates on the DB (required) while *reporting* Redis (optional) — visibility without fragility.
</details>
