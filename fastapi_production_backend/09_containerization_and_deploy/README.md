# Section 09 · Containerization & deploy

> **Prerequisites:** [08 · Observability & ops](../08_observability_and_ops/README.md), Docker installed · **Time:** ~2 h

The last mile: package TaskFlow so it runs identically anywhere, and deploy it safely. A multi-stage **Dockerfile**, a **docker-compose** stack (API + Postgres + Redis + worker), and a **production checklist** so nothing's forgotten.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 09-1 | [The Dockerfile](01_dockerfile.md) | How do I build a small, secure image that migrates on boot? |
| 09-2 | [Docker Compose stack](02_docker_compose.md) | How do I run the whole stack (API + DB + Redis + worker) locally? |
| 09-3 | [Deployment checklist](03_deployment_checklist.md) | What must be true before this goes to production? |

## What you'll be able to do after this section

- Write a multi-stage Dockerfile that runs as non-root and applies migrations on start.
- Compose the full stack with health-gated dependencies.
- Run through a concrete production readiness checklist.

→ Start: **[09-1 · The Dockerfile](01_dockerfile.md)**
