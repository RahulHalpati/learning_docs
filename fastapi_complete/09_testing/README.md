# Section 09 · Testing like you mean it

> **Prerequisites:** [08 · Redis: caching, rate limiting & background jobs](../08_redis_caching_jobs/README.md) · **Time:** ~5 h

An async app deserves async tests. This section builds a real test harness: **pytest** with pytest-asyncio in auto mode, **httpx** `AsyncClient` driving your app in-process through ASGI, and the **transaction rollback** pattern that gives every test a clean PostgreSQL database in milliseconds. By the end, `uv run pytest` is a single command you trust enough to deploy on.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 09-1 | [Pytest & async test setup](01_pytest_async_setup.md) | How do I test an async app in-process — fast, deterministic, no server? |
| 09-2 | [DB fixtures & transaction rollback](02_db_fixtures_rollback.md) | How does every test get a clean, real Postgres database in milliseconds? |
| 09-3 | [Mocking, fakes & overrides](03_mocking_and_overrides.md) | How do I swap auth, Redis, external APIs, and time — without touching app code? |

## Mini-project

Write the **full test suite for linkbox as it stands** — auth, links, caching, rate limiting, and Arq job enqueueing all get covered. One command runs everything: `uv run pytest`.

- [ ] `tests/conftest.py` with the core fixtures: session-scoped async **engine** (dockerized Postgres test DB), per-test rollback **`db_session`**, **`client`** (`AsyncClient` + `ASGITransport`, `get_db` overridden), and **`authed_client`** (client with a valid `Authorization` header for a freshly created user).
- [ ] **Auth flow**: register → login → `GET /me` → refresh-token rotation — and the old refresh token is **rejected** after it's been used once.
- [ ] **Owned-resource authorization**: user B tries to delete user A's link → `403`/`404` (whichever your API returns — assert the exact code), and the link **still exists** afterwards.
- [ ] **Validation errors**: invalid slug and invalid URL each return `422`, and the error body names the offending field.
- [ ] **Cache behavior** via fakeredis: first `GET /links/{slug}/stats` writes the cache key, second call is served from cache (assert via the fake — e.g. key exists / DB not hit again), and deleting the link **invalidates** the entry.
- [ ] **Rate limiting**: exceed the limit → `429` with a `Retry-After` header; under the limit → normal responses.
- [ ] **Arq**: deleting a link **enqueues** the cleanup job (assert against a fake pool: job name + args), and the job function itself is unit-tested directly with a `ctx` dict.
- [ ] **Coverage ≥ 80%** line coverage via pytest-cov, enforced with `--cov-fail-under=80` — so `uv run pytest` fails if coverage regresses.

## Test task (gate)

**The flaky-suite challenge.** You receive a test suite where **every test passes in isolation** (`pytest tests/api/test_links.py::test_x` → green) but the **full suite fails** — and *which* tests fail changes with ordering. Three defects are seeded:

1. A **module-scoped `db_session` fixture with no rollback** — rows created by one test leak into the next, so a "user already exists" or wrong-count assertion fails depending on what ran first.
2. A test that **mutates `app.dependency_overrides` and never cleans up** — every test that runs after it silently uses the overridden dependency.
3. An **async fixture whose event-loop scope doesn't match its callers** — session-scoped resource, function-scoped loop — producing `RuntimeError: ... attached to a different loop` partway through the run.

**Passing means, verifiably:**

1. All three defects **diagnosed in writing** before you fix them: for each, *what* leaked (rows, an override, a loop-bound connection), *why* the test order determined which victim failed, and why isolation hid it.
2. All three fixed using the patterns from this section (per-test rollback, override cleanup in fixture teardown, aligned `loop_scope`).
3. The full suite is green **run-to-run** — three consecutive runs, zero flakes.
4. It stays green both under `pytest -p no:randomly` **and** with **pytest-randomly** shuffling the order (multiple seeds). Order-independence is the proof that isolation is real, not accidental.

## What you'll be able to do after this section

- Configure pytest-asyncio (`asyncio_mode = "auto"`, loop scopes) and drive an async FastAPI app in-process with `httpx.AsyncClient` + `ASGITransport`.
- Give every test a clean, real PostgreSQL database via the connection-level transaction rollback pattern — including the savepoint variant for code that commits.
- Swap dependencies surgically with `app.dependency_overrides`, and choose fakes (fakeredis) over mocks where semantics matter.
- Intercept outbound HTTP with respx, control env and time with monkeypatch, and assert Arq enqueues without a worker.
- Diagnose test-order flakiness (leaked state, leaked overrides, loop mismatches) instead of rerunning until green.

→ Start: **[09-1 · Pytest & async test setup](01_pytest_async_setup.md)**
