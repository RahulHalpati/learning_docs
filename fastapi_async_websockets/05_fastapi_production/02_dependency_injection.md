# 02: Dependency injection

> **Level:** Intermediate · **Prerequisites:** [01 · Project structure](01_project_structure.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-03 (FastAPI 0.136.1)

## Why this matters

Dependency injection (DI) is FastAPI's signature feature and the thing that makes large apps clean. Instead of each endpoint creating its own database connection, reading its own config, and re-checking auth, it **declares what it needs** and FastAPI **provides it**. The payoff: no duplication, automatic setup/teardown, and the ability to swap real things for fakes in tests. If you learn one "advanced" FastAPI feature, learn this.

## Concept: `Depends` — declare a need, get it provided

A **dependency** is just a function. An endpoint asks for its result with `Depends`, and FastAPI calls it and passes the value in:

```python
from typing import Annotated
from fastapi import FastAPI, Depends

app = FastAPI()


def get_db():                          # a dependency: produces something the route needs
    return {"1": "apple", "2": "banana"}


@app.get("/items/{item_id}")
async def get_item(item_id: str, db: Annotated[dict, Depends(get_db)]):
    return {"item": db.get(item_id)}   # FastAPI called get_db() and passed the result as `db`
```

The modern, recommended syntax is **`Annotated[Type, Depends(func)]`**:

- `Annotated[dict, Depends(get_db)]` says: "this parameter is a `dict`, produced by `get_db`."
- FastAPI sees it, runs `get_db()` for each request, and injects the return value.
- It's just a function, so `get_db` can do anything — open a connection, read settings, validate a token.

> **Why `Annotated` over the older `db: dict = Depends(get_db)`?** The `Annotated` form keeps the type and the dependency together, works the same in path/query/body params, and — crucially — is **reusable**: you can alias it once and use it everywhere.

## Concept: reusable dependency aliases

Because `Annotated[...]` is a normal type, give it a name and reuse it across every endpoint. This is the idiom you'll see in real code:

```python
# app/api/deps.py
from typing import Annotated
from fastapi import Depends

def get_db():
    ...

DB = Annotated[dict, Depends(get_db)]      # define the "needs a db" type ONCE
```
```python
# any router
from app.api.deps import DB

@router.get("/items/{item_id}")
async def get_item(item_id: str, db: DB):  # clean, repeatable
    ...
```

One place defines how a DB is obtained; every endpoint just asks for `DB`.

## Concept: `yield` dependencies — setup *and* teardown

The real power: a dependency can **set something up, hand it over, then clean up afterward** using `yield` (just like the lifespan in [02.03](../02_fastapi_basics/03_calling_apis_async.md), but per-request). Everything before `yield` runs before the endpoint; everything after runs once the response is sent — even if the endpoint raised.

```python
def get_db_session():
    session = open_session()        # setup: runs before the endpoint
    try:
        yield session               # the endpoint runs with this value
    finally:
        session.close()             # teardown: ALWAYS runs after, even on error
```

This is *the* pattern for database sessions: open one per request, guarantee it's closed. The `try/finally` ensures cleanup even when the endpoint throws — no leaked connections.

```mermaid
flowchart LR
    A[request arrives] --> B["dependency: setup (before yield)"]
    B --> C[endpoint runs with the value]
    C --> D["dependency: teardown (after yield)"]
    D --> E[response sent]
    C -. even if it raises .-> D
```

## Concept: sub-dependencies (dependencies that need dependencies)

Dependencies can **depend on other dependencies**, and FastAPI resolves the whole chain. This is how you build `get_current_user` on top of `get_db` on top of `get_settings`:

```python
from typing import Annotated
from fastapi import Depends, HTTPException, Header

def get_db():
    return {"tokens": {"secret-abc": "Ada"}}

# this dependency USES get_db and reads a header
def get_current_user(
    db: Annotated[dict, Depends(get_db)],
    x_token: Annotated[str | None, Header()] = None,
):
    user = db["tokens"].get(x_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return user

CurrentUser = Annotated[str, Depends(get_current_user)]

@app.get("/me")
async def me(user: CurrentUser):       # depends on get_current_user, which depends on get_db
    return {"you_are": user}
```

The endpoint only asks for `CurrentUser`; FastAPI transparently runs `get_db`, reads the `X-Token` header, runs `get_current_user`, and — if auth fails — returns 401 **before the endpoint runs**. Endpoints stay focused on their job.

> **`Header()`** declares that `x_token` comes from the request header `X-Token` (underscores in the param name map to hyphens in the header). Like `Query`/`Path`, it's a parameter source.

## Verified: a dependency chain with setup/teardown and auth

```python
# deps_demo.py
from typing import Annotated
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.testclient import TestClient

events = []   # so we can observe setup/teardown order

def get_db():
    events.append("db: open")
    try:
        yield {"tokens": {"secret-abc": "Ada"}, "items": {"1": "apple"}}
    finally:
        events.append("db: close")

DB = Annotated[dict, Depends(get_db)]

def get_current_user(db: DB, x_token: Annotated[str | None, Header()] = None):
    user = db["tokens"].get(x_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return user

CurrentUser = Annotated[str, Depends(get_current_user)]

app = FastAPI()

@app.get("/items/{item_id}")
async def get_item(item_id: str, db: DB, user: CurrentUser):
    return {"item": db["items"].get(item_id), "requested_by": user}

client = TestClient(app)

print("no token   ->", client.get("/items/1").status_code,
      client.get("/items/1").json())
events.clear()
r = client.get("/items/1", headers={"X-Token": "secret-abc"})
print("good token ->", r.status_code, r.json())
print("event order->", events)
print("bad token  ->", client.get("/items/1", headers={"X-Token": "nope"}).status_code)
```

**Verified output:**

```
no token   -> 401 {'detail': 'Invalid or missing token'}
good token -> 200 {'item': 'apple', 'requested_by': 'Ada'}
event order-> ['db: open', 'db: close']
bad token  -> 401
```

Notice the `db: open` → `db: close` pair: the `yield` dependency set up and tore down around the request, exactly once. Auth ran as a sub-dependency and blocked the request before the endpoint when the token was bad.

## Concept: overriding dependencies in tests

Because endpoints depend on *functions*, tests can **swap those functions** for fakes via `app.dependency_overrides` — no real database needed. This is the single biggest reason DI matters for quality:

```python
def fake_db():
    yield {"tokens": {"test-token": "TestUser"}, "items": {"1": "TEST-ITEM"}}

app.dependency_overrides[get_db] = fake_db        # every get_db now returns the fake
# ... run tests against the fake ...
app.dependency_overrides.clear()                  # reset afterward
```

We'll use this properly in [Module 06](06_testing_logging_background.md), but the point stands: DI makes your app testable by construction.

## Concept: router- and app-level dependencies

To apply a dependency to **every** route in a router (e.g. require auth on all admin routes) without listing it on each, attach it to the router or app:

```python
from fastapi import APIRouter, Depends

# every route here requires a valid user; the value isn't needed, just the check
admin = APIRouter(prefix="/admin", dependencies=[Depends(get_current_user)])
```

`dependencies=[...]` runs the dependency for its **side effect** (the auth check / raising 401) without injecting a value. Great for cross-cutting requirements.

## Common mistakes

**Mistake: doing setup work without `yield` for things that need cleanup.** If a dependency opens a resource, use `yield` + `finally` so it's always closed. A plain `return` gives you no teardown hook.

**Mistake: heavy work in a dependency on every request.** A dependency runs **per request**. Don't create a new HTTP client or re-read a file each time — create expensive things once (lifespan / `@lru_cache`, see [Module 03](03_config_and_settings.md)) and inject the shared instance.

**Mistake: blocking the event loop in a dependency.** Dependencies follow the same async rules ([01.03](../01_async_python/03_async_io_httpx.md)): no `time.sleep`, no blocking DB calls in async code. Use `async def` deps with `await`, or push blocking work to a thread.

**Mistake: forgetting to clear `dependency_overrides`.** Leaving an override set leaks the fake into other tests. Always clear it (a fixture does this for you — Module 06).

## Practice

**Exercise:** Write a dependency `pagination` that reads query params `limit: int = 10` and `offset: int = 0`, returns them as a dict, and rejects `limit > 100` with a 400. Inject it into `GET /items` and confirm `?limit=200` is rejected while `?limit=5&offset=10` works.

<details><summary>Solution</summary>

```python
from typing import Annotated
from fastapi import Depends, HTTPException, Query

def pagination(limit: Annotated[int, Query(ge=1)] = 10,
               offset: Annotated[int, Query(ge=0)] = 0):
    if limit > 100:
        raise HTTPException(status_code=400, detail="limit cannot exceed 100")
    return {"limit": limit, "offset": offset}

Pagination = Annotated[dict, Depends(pagination)]

@app.get("/items")
async def list_items(page: Pagination):
    return {"page": page}
```

- `GET /items?limit=5&offset=10` → `{'page': {'limit': 5, 'offset': 10}}`
- `GET /items?limit=200` → `400 {'detail': 'limit cannot exceed 100'}`
- `GET /items?limit=0` → `422` (the `Query(ge=1)` constraint rejects it before our code runs)

(All verified.) A reusable `Pagination` dependency means every list endpoint gets consistent, validated paging for free.
</details>

## Recap & next

- ✅ Declare needs with **`Annotated[Type, Depends(func)]`**; FastAPI provides the value per request.
- ✅ Alias reusable dependencies (`DB = Annotated[...]`) and inject them everywhere.
- ✅ **`yield` dependencies** give per-request setup/teardown (the DB-session pattern) with guaranteed cleanup.
- ✅ Dependencies can depend on each other (`get_current_user` → `get_db`); failures raise before the endpoint.
- ✅ **`app.dependency_overrides`** swaps dependencies for fakes in tests; `dependencies=[...]` applies side-effect deps to a whole router.
- Self-check: when do you need a `yield` dependency instead of a plain `return` one?

→ Next: **[03 · Configuration & settings](03_config_and_settings.md)** — where config and secrets come from.
