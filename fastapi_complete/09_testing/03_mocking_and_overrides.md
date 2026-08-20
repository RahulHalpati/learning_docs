# 09-3 · Mocking, fakes & overrides

> **Level:** Intermediate · **Prerequisites:** [09-2 · DB fixtures & transaction rollback](02_db_fixtures_rollback.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (pytest · pytest-asyncio · httpx)

## Why this matters

A test suite that needs live Redis, a third-party API, and the real clock is slow, flaky, and can't run on an airplane. But replace those pieces carelessly — a `MagicMock` that happily returns a `MagicMock` for anything — and the suite goes green while the app is broken. This lesson is about replacing infrastructure *honestly*: the right seam (`dependency_overrides`), the right substitute (fakes with real semantics over mocks that agree with everything), and the right assertions.

---

## `dependency_overrides`: the front door

FastAPI's DI system is your test seam — you already used it for `get_db`. The same dict swaps *any* dependency. The classic: tests about **links** shouldn't spend requests logging in, so override the auth dependency:

```python
# tests/conftest.py
from app.main import app
from app.api.deps import get_current_user


@pytest.fixture
async def current_user(make_user):
    user = await make_user()
    # Every endpoint that depends on get_current_user now receives this user —
    # no token, no login round-trip. Auth ITSELF is tested in tests/api/test_auth.py.
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)   # teardown, ALWAYS
```

Two rules that keep this safe:

- **Override in a fixture, clean up in its teardown.** `app` is a module-level singleton — an override left behind applies to every later test in the run. That's seeded defect #2 in this section's gate, and it's depressingly common in real codebases.
- **Override the dependency, not the internals.** Reaching into `app.state` or monkeypatching a router function couples tests to wiring; `dependency_overrides` uses the same seam production uses.

Settings work the same way: override `get_settings` with a `Settings(...)` built for the test instead of exporting env vars and hoping caches cooperate.

---

## Fakes beat mocks (for infrastructure)

Two ways to replace Redis:

- A **mock** (`MagicMock`) records calls and returns whatever you program — and returns a truthy `MagicMock` for everything you *didn't* program. Ask it `await r.incr(key)` twice and it will not count; ask for a TTL and it will hand you an object that compares as true. **A mock agrees with your assumptions; it can't catch them being wrong.**
- A **fake** is a real implementation with a cheap backend. **fakeredis** *is* Redis semantics in memory: `INCR` actually counts, `EXPIRE` actually expires, `SETNX` actually races.

Prefer fakes for infrastructure, mocks for collaborators where only the *interaction* matters (below).

```python
import fakeredis
from app.core.redis import get_redis


@pytest.fixture
async def redis():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)  # real semantics, zero servers
    app.dependency_overrides[get_redis] = lambda: r
    yield r
    app.dependency_overrides.pop(get_redis, None)
    await r.aclose()
```

Now cache and rate-limit behavior is testable — *as behavior*, not as "we called Redis":

```python
async def test_stats_are_cached(client, current_user, redis, make_link):
    await make_link(slug="hot", owner=current_user)

    r1 = await client.get("/links/hot/stats")
    assert r1.status_code == 200
    assert await redis.exists("stats:hot")            # side effect: the cache was written

    await client.delete("/links/hot")
    assert not await redis.exists("stats:hot")        # delete invalidates — the bug this catches is real


async def test_login_rate_limit_returns_429(client, redis):
    bad = {"email": "x@test.dev", "password": "wrong"}
    for _ in range(5):                                # exhaust the window (limit = 5/min)
        await client.post("/auth/login", json=bad)

    resp = await client.post("/auth/login", json=bad)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers              # the contract, not just the code
```

The rate-limit test works because fakeredis's `INCR`/`EXPIRE` behave like Redis. A `MagicMock` would have "passed" this test no matter what the limiter did.

---

## respx: owning your outbound HTTP

When linkbox fetches a page title for link previews, tests must not hit the internet — slow, flaky, and you can't make example.com return a 500 on demand. **respx** intercepts outbound **httpx** calls at the transport level:

```python
import httpx
import respx


@respx.mock
async def test_preview_fetches_title(client, current_user):
    route = respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="<title>Example</title>")
    )

    resp = await client.post("/links", json={"url": "https://example.com/"})

    assert resp.status_code == 201
    assert route.called                            # assert the request we meant to make...
    assert resp.json()["title"] == "Example"       # ...and what we did with the response


@respx.mock
async def test_preview_timeout_degrades_gracefully(client, current_user):
    respx.get("https://slow.example/").mock(side_effect=httpx.ConnectTimeout)

    resp = await client.post("/links", json={"url": "https://slow.example/"})

    assert resp.status_code == 201                 # link still created —
    assert resp.json()["title"] is None            # a slow third party must not break OUR API
```

Three moves, every time: **assert the request happened** (`route.called`, or inspect `route.calls` for headers/body), **return a canned response**, and **simulate the ugly cases** — 500s, timeouts, garbage bodies. The failure-path tests are the valuable ones; the happy path was never in doubt.

---

## monkeypatch: env vars and the clock

pytest's built-in `monkeypatch` fixture patches attributes and env vars *and undoes everything automatically* at teardown — no leaks between tests:

```python
def test_slug_length_comes_from_env(monkeypatch):
    monkeypatch.setenv("LINKBOX_SLUG_LENGTH", "12")
    get_settings.cache_clear()          # settings are @lru_cache'd — clear or the old value wins
    assert get_settings().slug_length == 12


async def test_expired_token_is_rejected(monkeypatch):
    # Patch the seam, not time itself: security.py calls its own utcnow().
    from datetime import UTC, datetime
    monkeypatch.setattr("app.core.security.utcnow", lambda: datetime(2026, 1, 1, tzinfo=UTC))
    token = create_access_token(sub="1")                      # issued Jan 1...

    monkeypatch.setattr("app.core.security.utcnow", lambda: datetime(2026, 1, 2, tzinfo=UTC))
    with pytest.raises(ExpiredSignatureError):
        decode_token(token)                                   # ...validated "a day later"
```

Time tests are only possible because the code calls a **seam** (`security.utcnow()`) instead of `datetime.now()` inline — a one-line design choice that makes expiry logic testable and deterministic. If you need to freeze time across code you don't own, reach for **freezegun** (or the faster **time-machine**); for your own code, the patched seam is simpler.

---

## Testing Arq: the enqueue, then the job

Background jobs split into two independently testable halves. First: **did the endpoint enqueue the right job?** Fake the pool — it's a one-method protocol:

```python
class FakeArqPool:
    def __init__(self):
        self.jobs: list[tuple] = []

    async def enqueue_job(self, name, *args, **kwargs):
        self.jobs.append((name, args, kwargs))     # record; run nothing


@pytest.fixture
def arq_pool():
    pool = FakeArqPool()
    app.dependency_overrides[get_arq_pool] = lambda: pool
    yield pool
    app.dependency_overrides.pop(get_arq_pool, None)


async def test_delete_link_enqueues_purge(client, current_user, arq_pool, make_link):
    link = await make_link(owner=current_user)
    await client.delete(f"/links/{link.slug}")
    assert ("purge_link_stats", (link.slug,), {}) in arq_pool.jobs
```

Second: **does the job itself work?** An Arq task is just an async function whose first argument is a `ctx` dict — so call it directly with the pieces it uses:

```python
async def test_purge_job_deletes_stats(db_session, redis, make_link):
    link = await make_link(slug="dead")
    await redis.set("stats:dead", "42")

    await purge_link_stats({"redis": redis, "db": db_session}, "dead")   # ctx is just a dict

    assert not await redis.exists("stats:dead")
```

No worker, no queue, no sleeping in tests. The endpoint test proves the *handoff*; the job test proves the *work* — and neither needs the other to fail informatively.

---

## When a true mock is right: `AsyncMock`

Where only the **interaction** matters — "the welcome email was sent, once, to the right address" — a mock is the honest tool, because there's no semantics to fake:

```python
from unittest.mock import AsyncMock


async def test_register_sends_welcome_email(db_session):
    mailer = AsyncMock()                                   # awaitable methods, records calls
    service = AccountService(db=db_session, mailer=mailer)

    await service.register("new@test.dev", "s3cret-pass!")

    mailer.send_welcome.assert_awaited_once_with("new@test.dev")   # exactly once, exact args
```

`assert_awaited_once_with` is the whole point: it fails on zero calls, double calls, and wrong arguments. A mock without a call assertion is just a hole in the test.

---

## Coverage: the floor, not the goal

Wire **pytest-cov** into the default run so coverage is measured on every `uv run pytest`, and make the threshold a failing condition:

```toml
[tool.pytest.ini_options]
addopts = "-q --strict-markers --cov=app --cov-report=term-missing --cov-fail-under=80"
```

`term-missing` prints the exact uncovered lines — usually error branches, which is precisely where tests earn their keep. But be clear about what the number means: coverage proves lines *executed*, not behavior *verified*. A test that calls an endpoint and asserts nothing scores the same coverage as one that checks status, body, and side effect. 100% coverage with weak asserts is a well-lit empty room. **Assert quality beats line count** — use `--cov-fail-under` as a regression floor, never as the definition of done.

---

## Recap & next

- ✅ `app.dependency_overrides` is the front door: swap auth, settings, Redis, the Arq pool — always paired with teardown cleanup.
- ✅ **Fakes for infrastructure** (fakeredis = real Redis semantics), **mocks for interactions** (`AsyncMock` + `assert_awaited_once_with`). A `MagicMock` standing in for Redis agrees with everything and catches nothing.
- ✅ **respx** owns outbound httpx: assert the request, can the response, and always test the 500/timeout paths.
- ✅ **monkeypatch** for env and the clock (patch your `utcnow` seam); Arq = fake pool for the enqueue + direct call with a `ctx` dict for the job.
- ✅ pytest-cov with `--cov-fail-under=80` as a floor — and the humility to know what coverage doesn't prove.
- ✅ Self-check: your cache test passes with `MagicMock` in place of fakeredis but production caching is broken. What specifically did the mock hide?

→ Next: **[Section 10 · Robustness & observability](../10_robustness_observability/README.md)**

## Exercises

1. Using fakeredis, test that the rate-limit window actually *expires*: exhaust the limit, advance past the window, assert requests succeed again. (Hint: fakeredis `FakeRedis` accepts a fake clock via `time-machine`/`freezegun`, or expose the window key and `EXPIRE` it manually to simulate elapse.)

<details>
<summary>Solution</summary>

```python
async def test_rate_limit_window_expires(client, redis):
    bad = {"email": "x@test.dev", "password": "wrong"}
    for _ in range(5):
        await client.post("/auth/login", json=bad)
    assert (await client.post("/auth/login", json=bad)).status_code == 429

    # Simulate the window elapsing: kill the counter key the limiter uses.
    keys = await redis.keys("ratelimit:*")
    for k in keys:
        await redis.delete(k)

    assert (await client.post("/auth/login", json=bad)).status_code != 429
```

Deleting the key mimics TTL expiry deterministically (no sleeping). The test proves recovery, not just refusal — limits that never reset are an outage, not a feature.
</details>

2. With respx, make the preview fetch return `500`, then a body with no `<title>`. Assert linkbox degrades the same way in both cases. Why test both when the handling code might be one `except` block?

<details>
<summary>Solution</summary>

```python
@respx.mock
async def test_preview_upstream_500(client, current_user):
    respx.get("https://down.example/").mock(return_value=httpx.Response(500))
    resp = await client.post("/links", json={"url": "https://down.example/"})
    assert resp.status_code == 201 and resp.json()["title"] is None

@respx.mock
async def test_preview_no_title_tag(client, current_user):
    respx.get("https://bare.example/").mock(return_value=httpx.Response(200, text="<p>hi</p>"))
    resp = await client.post("/links", json={"url": "https://bare.example/"})
    assert resp.status_code == 201 and resp.json()["title"] is None
```

They're different failure *categories*: a transport/status error versus a successful response with unusable content. Today one `except` might catch both; tomorrow someone refactors parsing and only breaks the second path. Tests pin behavior per category, not per implementation.
</details>

3. Write a test that reaches 100% line coverage of this function yet misses its bug — then fix the *assert* (not the coverage):

```python
def remaining_attempts(used: int, limit: int = 5) -> int:
    return limit - used   # bug: can go negative
```

<details>
<summary>Solution</summary>

```python
def test_remaining_attempts():
    assert remaining_attempts(2) == 3          # 100% coverage — one line, executed. Bug missed.

def test_remaining_attempts_never_negative():
    assert remaining_attempts(7) == 0          # fails: returns -2. THIS assert finds the bug.
```

Both suites report identical coverage; only the second one tests the *property that matters* (never negative). That's the whole coverage lesson in four lines: the metric counts execution, only assertions count as verification.
</details>
