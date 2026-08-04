# 07-2 · Rate limiting

> **Level:** Intermediate · **Prerequisites:** [07-1 · Redis caching](01_redis_caching.md)
> **Time:** 25 min · **Verified:** 2026-07-27 (redis-py 5.3.1, Redis server 6.0.16)

## Why this matters

Without a rate limit, one client can hammer your API — accidentally (a retry storm) or maliciously (abuse, credential stuffing on `/login`). The limit must be **shared across workers**, so it lives in Redis, and it's cleanest as a **dependency** you attach to the routes that need it.

---

## A rate-limit dependency

Fixed window: count requests per `(client, window)` with an atomic `INCR`, deny over the limit:

```python
# app/integrations/ratelimit.py
import time
from fastapi import Depends, Request
from app.core.exceptions import AppError
from app.integrations.redis_client import get_redis

class RateLimitError(AppError):
    status_code, code = 429, "rate_limited"

def rate_limiter(limit=100, window=60):
    async def dependency(request: Request) -> None:
        r = get_redis()
        identity = request.client.host if request.client else "anon"
        key = f"rl:{identity}:{int(time.time()) // window}"
        count = await r.incr(key)                 # atomic
        if count == 1:
            await r.expire(key, window)           # first hit sets the TTL
        if count > limit:
            raise RateLimitError("Rate limit exceeded. Try again later.")
    return Depends(dependency)
```

Attach it where it matters — especially auth endpoints:

```python
@router.post("/login", dependencies=[rate_limiter(limit=5, window=60)])
async def login(...): ...        # ≤ 5 login attempts/min per IP
```

**Output (real run, limit 5):**
```
requests 1–5: allowed
requests 6–7: denied (429)
```

The `RateLimitError` is an `AppError`, so it flows through the same handler as every other error ([05-2](../05_api_design_and_robustness/02_error_handling.md)) — returning your uniform JSON with a **429** status. Because the counter is in Redis, all workers enforce one shared limit.

---

## Choosing the limit and the identity

- **Identity:** an API key or user id for authenticated endpoints; the client IP for anonymous ones (but IPs are shared behind NAT/proxies — behind a load balancer, read the real IP from `X-Forwarded-For`, carefully).
- **Limit:** tight on sensitive endpoints (login, register, password reset — this throttles brute-force), looser on general reads. Return a `Retry-After` header so good clients back off.

> **Tip — layered limits.** A global limit protects the service; a stricter per-endpoint limit protects sensitive routes. Apply `rate_limiter()` globally (as a router dependency) *and* a tighter one on `/login`. Algorithms (fixed vs sliding window vs token bucket) are covered in the [async course's 06-3](../../fastapi_async_websockets/README.md); fixed window is the right default.

---

## Recap & next

- ✅ Rate limits live in **Redis** so every worker shares the count.
- ✅ Implement as a **dependency** (`rate_limiter(limit, window)`); it raises a **429** through your error handler.
- ✅ Limit sensitive endpoints (login/register) tightly to throttle abuse; choose the right identity.
- ✅ Layer a global limit with stricter per-route limits.
- ✅ Self-check: why must the rate-limit counter be in Redis rather than a Python variable in the worker?

→ Next: **[07-3 · Background jobs (arq)](03_background_jobs.md)**

## Exercises

1. Apply a global `rate_limiter()` to the whole `api_router` and a stricter one to `/auth/login`. Confirm login is throttled sooner than general reads.

<details>
<summary>Solution</summary>

`APIRouter(prefix="/api/v1", dependencies=[rate_limiter(100, 60)])` for the global cap, plus `dependencies=[rate_limiter(5, 60)]` on the login route. Login denies after 5/min; other routes after 100/min — layered protection.
</details>
