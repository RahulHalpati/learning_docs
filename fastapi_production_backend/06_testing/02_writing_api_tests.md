# 06-2 · Writing API tests

> **Level:** Intermediate · **Prerequisites:** [06-1 · Test setup & fixtures](01_test_setup_fixtures.md)
> **Time:** 40 min · **Verified:** 2026-07-27 (the TaskFlow suite: 13 passed)

## Why this matters

With fixtures in place, tests are short and read like a spec. Good API tests cover more than the happy path — they assert **validation**, **auth (401/403)**, and **isolation** between users. These are exactly the things that break in production, and exactly what a demo never checks.

---

## Happy path + a security assertion

```python
async def test_register_and_login(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "a@b.com", "password": "password123", "full_name": "Ada"})
    assert r.status_code == 201
    assert "hashed_password" not in r.json()          # ← the hash must never leak

    r = await client.post("/api/v1/auth/login",
                          data={"username": "a@b.com", "password": "password123"})
    assert {"access_token", "refresh_token"} <= r.json().keys()
```

That `"hashed_password" not in r.json()` is a *security regression test*: if someone ever adds the field to `UserRead`, this test fails. Tests encode the rules you care about.

---

## Test the unhappy paths

Production breaks on the edges — test them explicitly:

```python
async def test_duplicate_email_conflicts(client):
    body = {"email": "dup@b.com", "password": "password123", "full_name": "X"}
    await client.post("/api/v1/auth/register", json=body)
    r = await client.post("/api/v1/auth/register", json=body)
    assert r.status_code == 409                       # conflict
    assert r.json()["error"]["code"] == "conflict"    # our uniform error shape

async def test_protected_route_requires_token(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401

async def test_refresh_rejects_access_token(client):
    # ... register + login ...
    bad = await client.post("/api/v1/auth/refresh",
                            json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401                     # access token ≠ refresh token
```

Each asserts a *rule* from earlier sections — the conflict shape (05-2), auth requirement (04-3), token-type enforcement (04-2). Tests are where those rules become guarantees.

---

## Ownership isolation — the multi-tenant test

The most important test in a multi-user app: user B **cannot** see or touch user A's data.

```python
async def test_ownership_isolation(client):
    # A creates a project ...
    pid = (await client.post("/api/v1/projects", headers=ha, json={"name": "secret"})).json()["id"]
    # ... B must be denied and must see none of it
    assert (await client.get(f"/api/v1/projects/{pid}", headers=hb)).status_code == 403
    assert (await client.get("/api/v1/projects", headers=hb)).json()["total"] == 0
```

If ownership ever regresses, this test goes red before the leak reaches production.

---

## Run the suite

```bash
pytest -q
```

**Output (real run):**
```
.............                                                            [100%]
13 passed in 3.90s
```

Thirteen tests — auth flow, CRUD, pagination, status filtering, ownership isolation, health probes, and the Redis integrations (which skip if Redis is absent) — in under 4 seconds, offline. Fast enough to run on every save and in CI on every push.

> **Tip — test behavior, not implementation.** Assert on responses (status, JSON, headers), not on internal calls. Then you can refactor services/repositories freely and the tests still guarantee the API contract. Aim to cover every rule you'd be embarrassed to break: auth, isolation, validation, and the core happy paths.

---

## What to test (a checklist)

| Category | Example |
|----------|---------|
| Happy path | create → read → update → delete works |
| Validation | bad body → 422; bad enum → 422 |
| AuthN | no token → 401; bad token → 401 |
| AuthZ | wrong user → 403; non-admin on admin route → 403 |
| Isolation | user B can't see user A's rows |
| Edge cases | pagination bounds, empty lists, not-found → 404 |

---

## Recap & next

- ✅ Tests read like a spec: happy path **plus** validation, auth (401/403), and isolation.
- ✅ Encode security rules as tests (e.g. "the hash never appears in a response").
- ✅ The suite runs fast and offline (SQLite) — 13 passed in ~4s — ready for CI.
- ✅ Test **behavior** (responses), not implementation, so refactors stay safe.
- ✅ Self-check: which single test would catch a regression that lets one user read another's projects?

→ Next: **[07 · Integrations](../07_integrations/README.md)**

## Exercises

1. Write `test_pagination_bounds`: create 3 projects, request `?size=200`, and assert the effective size is capped at 100 (the `le=100` limit).

<details>
<summary>Solution</summary>

Create 3 projects, `GET /api/v1/projects?size=200`. FastAPI's `Query(size, le=100)` rejects `size=200` with **422** — so assert `status_code == 422`. (To test the cap silently clamping instead, change the dependency to `min(size, 100)` and assert `body["size"] == 100`.) Either way you've pinned the bound.
</details>
