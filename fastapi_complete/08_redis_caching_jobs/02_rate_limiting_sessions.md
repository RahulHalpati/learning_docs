# 08-2 · Rate limiting & sessions

> **Level:** Intermediate · **Prerequisites:** [08-1 · Redis & cache-aside caching](01_redis_asyncio_caching.md)
> **Time:** ~50 min · **Verified:** 2026-08-07 (redis-py asyncio · Arq · Redis 7)

## Why this matters

`POST /auth/token` is a password oracle: without a limit, an attacker runs a dictionary attack at network speed against real accounts. Beyond auth, unthrottled endpoints invite scrapers, runaway clients, and cost bombs (every request is DB load — or, on modern backends, a paid LLM call). Rate limiting is availability armor: it bounds the blast radius any single client can inflict, so one bad actor degrades *their* experience instead of everyone's. It has to live in Redis for the same reason the cache does — a per-process counter resets on every deploy and disagrees across replicas.

---

## Fixed window: INCR + EXPIRE

The simplest limiter: count requests per key per time window, reject above the limit.

```python
# limit=5, window=60 → the key expires 60 s after the FIRST hit in the window
async def fixed_window_ok(redis: Redis, key: str, limit: int, window: int) -> bool:
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(key)                        # atomic count — Redis runs commands one at a time
        pipe.expire(key, window, nx=True)     # set TTL only if the key has none (Redis 7+)
        count, _ = await pipe.execute()
    return count <= limit
```

The pipeline with `transaction=True` wraps both commands in MULTI/EXEC, so a crash can't leave an immortal counter with no TTL. `INCR` being atomic means this is correct across every replica with zero locks — the single-threaded execution from 08-1 paying off.

**The flaw: boundary bursts.** "5 per minute" here means 5 per *clock window*. A client can send 5 requests at 0:59 and 5 more at 1:01 — 10 in two seconds, twice the intended rate, perfectly "legal". Fixed window is fine for coarse limits where 2× bursts don't hurt; login throttling deserves better.

---

## Sliding window: a sorted set of timestamps

Store each request as a **sorted-set member scored by its timestamp**. The window then slides continuously: "the last 60 seconds" always means exactly that.

```python
# app/api/ratelimit.py
import time
import uuid

from fastapi import HTTPException
from redis.asyncio import Redis


async def sliding_window_hit(redis: Redis, key: str, limit: int, window: int) -> None:
    """Record one request under `key`; raise 429 if over `limit` per `window` seconds."""
    now = time.time()
    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, now - window)   # 1. evict events older than the window
        pipe.zadd(key, {f"{now}:{uuid.uuid4().hex[:6]}": now})  # 2. record this request
        pipe.zcard(key)                               # 3. count what's left in the window
        pipe.expire(key, window)                      # 4. GC the whole key once idle
        _, _, count, _ = await pipe.execute()

    if count > limit:
        # Retry-After = when the oldest event slides out of the window
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        retry = max(1, int(oldest[0][1] + window - now) + 1) if oldest else window
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry)},  # tell well-behaved clients when to return
        )
```

Details that matter: the member string gets a random suffix because sorted-set members must be **unique** — two requests landing on the same float timestamp would otherwise count as one. The `429` carries **`Retry-After`** (seconds), the standard header that turns your limiter from a wall into a contract — SDKs and proxies honor it. Cost: O(window size) memory per key versus the fixed window's single integer; that's the price of accuracy.

Now wrap it as a **parameterized dependency** so any endpoint can opt in with one line:

```python
from fastapi import Request

def rate_limit_ip(limit: int, window: int, scope: str):
    async def dep(request: Request, redis: RedisDep) -> None:
        ip = request.client.host                      # see the proxy caveat below
        await sliding_window_hit(redis, f"rl:{scope}:ip:{ip}", limit, window)
    return dep

def rate_limit_user(limit: int, window: int, scope: str):
    async def dep(user: CurrentUser, redis: RedisDep) -> None:  # from Section 07
        await sliding_window_hit(redis, f"rl:{scope}:user:{user.id}", limit, window)
    return dep
```

```python
@router.post("/auth/token", dependencies=[Depends(rate_limit_ip(5, 60, "token"))])
async def login(...): ...

@router.post("/links", dependencies=[Depends(rate_limit_user(30, 60, "create"))])
async def create_link(...): ...
```

---

## What do you key by?

The key decides *whose* bucket a request lands in — get it wrong and the limiter protects nothing.

- **IP** — the only identity you have *before* auth, so it's what guards `/auth/token`. Two caveats: behind a reverse proxy, `request.client.host` is the **proxy's** IP, so every user shares one bucket and you rate limit yourself into an outage. `X-Forwarded-For` fixes that **only behind your own proxy** (run uvicorn with `--proxy-headers --forwarded-allow-ips` so it rewrites `request.client`); trusting XFF from the open internet lets attackers choose their own key, since it's just a client-controlled header. And IPs are shared (offices, CGNAT) — keep IP limits coarse.
- **User id (JWT `sub`)** — precise, survives IP hopping, but only exists after auth.
- **API key** — for machine clients; conveniently it's also the billing identity.

**Layer them.** A coarse per-IP limit protects the login endpoint itself; per-user limits protect resources after login. Neither replaces the other: an attacker with many IPs walks around per-IP limits (this section's gate makes you prove it), and an unauthenticated attacker has no user id to key on.

---

## Redis-backed sessions: revocation JWTs can't do

Section 07's access JWTs are stateless: valid until `exp`, *no matter what* — you cannot un-issue one. Server-side sessions flip that trade: the browser holds only a random id in an **HttpOnly cookie**; everything else lives in a Redis hash you can delete at will.

```python
# app/services/sessions.py
import secrets
import time

from redis.asyncio import Redis

SESSION_TTL = 60 * 60 * 24 * 7   # 7 days of inactivity logs you out


async def create_session(redis: Redis, user_id: int) -> str:
    sid = secrets.token_urlsafe(32)   # unguessable — the id IS the credential
    key = f"session:{sid}"
    await redis.hset(key, mapping={"user_id": user_id, "created_at": int(time.time())})
    await redis.expire(key, SESSION_TTL)
    return sid


async def load_session(redis: Redis, sid: str) -> dict | None:
    key = f"session:{sid}"
    data = await redis.hgetall(key)
    if not data:
        return None                       # expired or revoked — same outcome
    await redis.expire(key, SESSION_TTL)  # sliding expiration: activity keeps it alive
    return data


async def revoke_session(redis: Redis, sid: str) -> None:
    await redis.delete(f"session:{sid}")  # effective on the very next request
```

Set the cookie on login: `response.set_cookie("session_id", sid, httponly=True, secure=True, samesite="lax", max_age=SESSION_TTL)` — `httponly` keeps XSS from reading it. The `EXPIRE` on every read gives **sliding expiration**: active users stay logged in, abandoned sessions die after 7 quiet days. And `revoke_session` is the headline: "log out everywhere, *now*" is one `DELETE` — the exact thing a JWT cannot do. The price is a Redis hop on every request; that's the stateless-vs-revocable trade in one line.

---

## The JWT `jti` denylist, for real

Section 07 rotated refresh tokens and promised a denylist for revoked ones. A denylist entry only needs to exist while the token it blocks is still alive — so give it **TTL = the token's remaining lifetime** and it cleans up after itself:

```python
# app/services/token_denylist.py
import time

from redis.asyncio import Redis


async def revoke_jti(redis: Redis, jti: str, exp: int) -> None:
    ttl = exp - int(time.time())
    if ttl > 0:  # an already-expired token is rejected by the exp check anyway
        await redis.setex(f"denylist:jti:{jti}", ttl, "1")


async def jti_revoked(redis: Redis, jti: str) -> bool:
    return await redis.exists(f"denylist:jti:{jti}") == 1
```

Wire it into Section 07's refresh flow: on logout and on every rotation, `revoke_jti` the old token; in `POST /auth/refresh`, check `jti_revoked` *before* issuing new tokens (a revoked `jti` showing up again is the token-theft signal from 06 — treat it as hostile). Because entries expire exactly when their token does, the denylist's size is bounded by "tokens that are both revoked *and* still unexpired" — always small, never scanned, never migrated.

---

## Recap & next

- ✅ Fixed window = `INCR` + `EXPIRE` — one integer per key, but permits 2× bursts across window boundaries.
- ✅ Sliding window = sorted set: `ZREMRANGEBYSCORE` (evict) → `ZADD` (record) → `ZCARD` (count), in one transactional pipeline; reject with **429 + `Retry-After`**.
- ✅ Key by IP pre-auth (trust `X-Forwarded-For` only behind *your* proxy), by user/API key post-auth — and layer both.
- ✅ Redis sessions: HttpOnly cookie → `session:{id}` hash, sliding `EXPIRE` on access, **instant revocation** via `DELETE` — the trade JWTs can't make.
- ✅ `jti` denylist: `SETEX` with TTL = remaining token lifetime → self-cleaning, bounded memory.
- ✅ Self-check: why does the denylist entry's TTL equal the token's *remaining* lifetime rather than some fixed value?

→ Next: **[08-3 · Background jobs with Arq](03_background_jobs_arq.md)**

## Exercises

1. Burst math: an endpoint uses a **fixed** window of 100/hour. What's the maximum number of requests a client can land in a single 2-minute span without ever being limited? What does the sliding window allow in the same span?

<details>
<summary>Solution</summary>

200: 100 requests at 0:59:00–0:59:59 (filling hour N's window) and 100 more at 1:00:00–1:00:59 (hour N+1's fresh window) — twice the intended rate, concentrated into two minutes. The sliding window allows exactly 100 in *any* 60-minute span, so at most 100 in those 2 minutes, and then nothing for the next 58.
</details>

2. Verify your login limiter end to end with curl: prove the 6th attempt within a minute gets `429` with a sane `Retry-After`.

<details>
<summary>Solution</summary>

```bash
for i in 1 2 3 4 5 6; do
  curl -s -o /dev/null -D - -X POST localhost:8000/auth/token \
    -d "username=x@y.com&password=wrong" | grep -E "HTTP|Retry-After"
done
```

Expected: five `HTTP/1.1 401` (wrong password, but *counted* — attempts are limited whether or not they succeed), then `HTTP/1.1 429` with `Retry-After: ~55` (the oldest of the five attempts needs ~55 more seconds to slide out of the 60 s window). If attempt 6 still returns 401, your limiter dependency isn't on the route — or each request built its own Redis client and its own empty bucket.
</details>

3. Design question: why a *deny*list of revoked `jti`s instead of an *allow*list of valid ones?

<details>
<summary>Solution</summary>

Size and failure mode. An allowlist holds an entry for **every live token** of every user and must be written on every issue — big, hot, and load-bearing. The denylist holds only "revoked but not yet expired" tokens — tiny, usually empty. Failure modes differ too: if Redis is down, an allowlist fails **closed** (nobody can refresh — full outage), a denylist fails **open** (revocation is delayed until Redis returns, but normal users are unaffected). For refresh tokens that's usually the right trade; flip to an allowlist only when "revocation must hold even during a cache outage" is a hard requirement — at which point reconsider server-side sessions, which give you that property natively.
</details>
