# Section 07 · Integrations

> **Prerequisites:** [03 · Schemas & CRUD](../03_schemas_and_crud/README.md) · **Time:** ~2 h

A production service leans on a few external systems. This section adds the essential ones for TaskFlow: **Redis** for caching and rate limiting, and **arq** for background jobs. (The companion [async course's Section 06](../../fastapi_async_websockets/README.md) covers Redis scaling in more depth — including pub/sub for WebSockets — so here we focus on applying it in this service.)

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 07-1 | [Redis caching](01_redis_caching.md) | How do I cache read-heavy responses to cut DB load? |
| 07-2 | [Rate limiting](02_rate_limiting.md) | How do I limit requests per client across all workers? |
| 07-3 | [Background jobs (arq)](03_background_jobs.md) | How do I run slow work off the request path? |

## What you'll be able to do after this section

- Add a cache-aside layer with Redis and a TTL.
- Enforce distributed rate limits as a dependency.
- Offload slow work (email, reports) to an arq worker.

> **Setup:** these need a Redis server (`redis-server`, or the `docker-compose.yml` service). The app runs fine without them; the integrations are additive.

→ Start: **[07-1 · Redis caching](01_redis_caching.md)**
