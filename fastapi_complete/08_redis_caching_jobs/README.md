# Section 08 · Redis: caching, rate limiting & background jobs

> **Prerequisites:** [07 · Security & authentication](../07_security_auth/README.md) · **Time:** ~5 h

Postgres is your source of truth, but every answer costs a disk-bound round trip — and some questions (is this the sixth login attempt this minute?) it shouldn't be answering at all. This section adds **Redis** as your service's fast shared state: **cache-aside** reads that cut latency and database load, **rate limiting** that bounds brute force and blast radius, and **Arq** background jobs so no user ever waits on email or webhooks. One asyncio client, created in lifespan and injected like your DB session, powers all three.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 08-1 | [Redis & cache-aside caching](01_redis_asyncio_caching.md) | How do I share fast state across replicas and cache DB reads — without serving stale data forever? |
| 08-2 | [Rate limiting & sessions](02_rate_limiting_sessions.md) | How do I throttle brute force with correct 429s — and revoke a session *instantly*? |
| 08-3 | [Background jobs with Arq](03_background_jobs_arq.md) | How do I run slow work (email, webhooks, cleanup) without making a request wait? |
| 08-4 | [Pub/sub & cross-worker real-time](04_pubsub_realtime.md) | How do I broadcast an event to every worker's clients when each process only holds its own? |

## Mini-project

Wire Redis into **linkbox** end to end. You need Redis 7 running locally (the docker command is in 08-1) and `uv add redis arq`, with `REDIS_URL=redis://localhost:6379/0` in `.env`.

**Requirements checklist:**

- [ ] One Redis client per process: `Redis.from_url(...)` created in **lifespan**, closed on shutdown, injected everywhere via the `RedisDep` alias — no endpoint creates its own client.
- [ ] **Cache-aside** on `GET /{slug}` resolution *and* `GET /links/{slug}/stats`, TTL from settings (`CACHE_TTL_SECONDS`), keys versioned (`links:{slug}:v1`), values serialized with Pydantic `model_dump_json` / `model_validate_json`.
- [ ] Cache **invalidated (key deleted) on link update and delete** — a changed or removed link never redirects stale past the write.
- [ ] **Sliding-window rate limit** on `POST /auth/token`: 5/min per IP, rejecting with **429 + `Retry-After`**.
- [ ] **Per-user rate limit** on link creation (`POST /links`, e.g. 30/min), keyed by the JWT `sub` — not by IP.
- [ ] **Arq worker** with a `send_welcome_email(ctx, user_id, email)` job that *logs* instead of hitting real SMTP, enqueued on `POST /auth/register`, with retry config (`max_tries`, `Retry(defer=...)` on transient failure). Worker runs via `uv run arq app.worker.WorkerSettings`.
- [ ] The **refresh-token denylist from Section 07 implemented for real**: on logout/rotation, the token's `jti` goes into Redis with **TTL = the token's remaining lifetime**; the refresh flow rejects revoked `jti`s.

## Test task (gate)

A staleness + abuse drill. Plant these two bugs into your mini-project **as-is**, then find, prove, and fix them. Complete both parts before starting Section 09.

**Bug 1 — the immortal redirect.** Replace your delete endpoint with this version (DB delete, no cache invalidation):

```python
@router.delete("/links/{slug}", status_code=204)
async def delete_link(slug: str, db: DbSession, user: CurrentUser) -> None:
    await db.execute(delete(Link).where(Link.slug == slug, Link.owner_id == user.id))
    # nothing else — that's the bug
```

Prove the bug with a reproduction transcript: create a link, `GET /{slug}` once (this populates the cache), `DELETE` it, then show `GET /{slug}` **still returns 307** and redirects to the deleted URL. Then fix it (delete the cache key in the delete path, after the DB write) and prove it's gone: the same sequence now returns **404 immediately** after delete.

**Bug 2 — the many-headed attacker.** Change the `POST /links` rate limit to key **only by IP** (`rate_limit_ip(30, 60, "create")`). One authenticated attacker with one JWT behind many IPs now gets `30 × N` creations per minute — per-user limits are bypassed entirely. Demonstrate it locally: key the limiter off `X-Forwarded-For` and vary the header across requests with the *same* token — each fake IP gets a fresh bucket (this is also exactly why you never trust client-controlled headers as limiter keys). Then **rekey correctly** by the JWT `sub` and show the cap holds no matter how many "IPs" the token arrives from.

**Passing =** both reproduction-then-fix transcripts (bug reproduced, fix applied, same probe now clean), **plus** a short written note on what TTL alone does **not** fix: TTL bounds the *staleness window* — how long a wrong answer can live — but it never gives read-after-write *correctness*. A deleted link that redirects for another 300 seconds is a correctness (and potentially security) bug that only explicit invalidation fixes; shrinking the TTL just shrinks how long you're wrong.

## What you'll be able to do after this section

- Run Redis beside your API: one asyncio client per process, created in lifespan, injected via `RedisDep`.
- Implement cache-aside with versioned keys, TTLs, Pydantic serialization, and delete-on-write invalidation — and explain why TTL is a staleness bound, not correctness.
- Rate limit any endpoint with fixed- or sliding-window dependencies returning proper `429 + Retry-After`, keyed by IP, user, or both layered.
- Store sessions and a JWT `jti` denylist in Redis with instant revocation — the thing stateless JWTs can't do.
- Offload slow work to an Arq worker with retries, cron schedules, and idempotent job design.
- Broadcast events across workers with Redis pub/sub (cross-process WebSocket fan-out) — and know when to reach for Streams instead.

→ Start: **[08-1 · Redis & cache-aside caching](01_redis_asyncio_caching.md)**
