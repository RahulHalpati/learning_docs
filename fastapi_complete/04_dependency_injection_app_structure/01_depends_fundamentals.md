# 04-1 · Depends fundamentals

> **Level:** Beginner→Intermediate · **Prerequisites:** [02 · FastAPI fundamentals & Pydantic v2](../02_fastapi_fundamentals_pydantic/README.md)
> **Time:** ~40 min · **Verified:** 2026-08-07 (FastAPI 0.116 · Pydantic 2.11)

## Why this matters

Every real endpoint needs things — settings, storage, the current user — and *how* those things arrive decides whether the app is testable or a tangle of hidden globals. `Depends` makes every requirement explicit in the function signature: FastAPI builds it per request, caches it within the request, and lets tests substitute it without touching the code under test. This one mechanism is why FastAPI apps stay swappable as they grow.

---

## The problem with globals

```python
# the tutorial way — a module-level global
from app.core.config import settings        # constructed at IMPORT time

@app.get("/info")
def info():
    return {"app": settings.app_name}        # hidden input — the signature lies
```

Three failure modes baked in:

- **Import-time construction.** `AppSettings()` runs the moment anything imports the module — a missing env var crashes even a unit test that never touches settings.
- **Invisible coupling.** Nothing in `info`'s signature says it needs settings; you discover the dependency by reading the body (or at 3am).
- **No substitution.** Tests can monkeypatch the module attribute, but every import site holds its own reference — fragile and whack-a-mole.

DI inverts this: the endpoint *declares* what it needs, the framework *provides* it per request.

---

## Function dependencies + the Annotated alias

A dependency is just a callable. Settings become one:

```python
# app/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LINKBOX_")
    app_name: str = "linkbox"
    debug: bool = False

@lru_cache                          # built once per process, on FIRST USE — not at import
def get_settings() -> AppSettings:
    return AppSettings()
```

```python
# app/api/deps.py
from typing import Annotated
from fastapi import Depends
from app.core.config import AppSettings, get_settings

Settings = Annotated[AppSettings, Depends(get_settings)]
```

```python
@app.get("/info")
def info(settings: Settings):        # the requirement is now IN the signature
    return {"app": settings.app_name, "debug": settings.debug}
```

- **`Annotated[X, Depends(dep)]`** is the 2026-standard style — the alias is defined once, reused everywhere, and greppable. No `= Depends(...)` default values scattered through signatures.
- Dependencies can be `def` or `async def`; sync ones run in a threadpool so they don't block the event loop.
- Because the endpoint asks for *"an `AppSettings`, provided by `get_settings`"*, tests can later swap the provider without the endpoint noticing — that's the whole game.

---

## Sub-dependencies: deps that depend on deps

Dependencies declare their own dependencies (and even path parameters); FastAPI solves the whole tree per request:

```python
# app/api/deps.py
from fastapi import HTTPException

def get_store() -> LinkStore:                    # storage provider (lesson 04-3 wires it up)
    return _store

Store = Annotated[LinkStore, Depends(get_store)]

def get_link_or_404(code: str, store: Store) -> Link:   # depends on Store AND the path param
    link = store.get(code)
    if link is None:
        raise HTTPException(status_code=404, detail=f"unknown code {code!r}")
    return link

CurrentLink = Annotated[Link, Depends(get_link_or_404)]
```

```python
@app.get("/links/{code}")
def resolve(link: CurrentLink):     # 404 handling happened BEFORE the body runs
    return RedirectResponse(link.url)

@app.delete("/links/{code}", status_code=204)
def remove(link: CurrentLink, store: Store):
    store.delete(link.code)
```

The 404 check lives in exactly one place. Every endpoint that needs "a valid link" declares `CurrentLink` — duplicate lookup-and-raise blocks are the first thing sub-dependencies delete from a codebase.

---

## Per-request caching (and opting out)

Within one request, each dependency runs **once**, no matter how many places declare it:

```python
import uuid

def request_id() -> str:
    print("generating...")                  # watch the console: prints ONCE per request
    return uuid.uuid4().hex

RequestId = Annotated[str, Depends(request_id)]

@app.get("/cache-demo")
def cache_demo(a: RequestId, b: RequestId):
    return {"same": a == b}                 # True — second use hit the request cache
```

Why this matters: when `Settings` appears in five sub-dependencies, `get_settings` is solved once; when a DB session dependency is used by both an auth check and the endpoint, they share the *same* session — one transaction, not two. To force a fresh value each time, opt out:

```python
FreshId = Annotated[str, Depends(request_id, use_cache=False)]   # runs on every use
```

The cache key is the dependency callable itself, and it lives only for the request — nothing leaks across requests.

---

## Class-based dependencies

Any callable works, so a class (its `__init__` is the signature FastAPI inspects) can bundle related parameters *with logic* — something bare query params can't do:

```python
class Pagination:
    def __init__(self, limit: int = 20, offset: int = 0) -> None:
        self.limit = min(max(limit, 1), 100)   # clamp — no ?limit=100000 table scans
        self.offset = max(offset, 0)

Page = Annotated[Pagination, Depends()]        # Depends() with no arg: class inferred from the annotation

@app.get("/links")
def list_links(page: Page, store: Store):
    return store.list(limit=page.limit, offset=page.offset)
```

You get a typed object (`page.limit`, editor autocomplete) instead of loose ints, and the clamping rule exists once instead of in every list endpoint.

---

## Parameterized dependencies

Sometimes you need a *family* of dependencies — "require role X" for varying X. A dependency can't take your arguments at request time, so build it with a closure (or a class with `__call__`):

```python
from fastapi import Header, HTTPException

def require_role(role: str):
    def checker(x_role: Annotated[str, Header()] = "guest") -> None:
        if x_role != role:
            raise HTTPException(status_code=403, detail=f"requires role {role!r}")
    return checker

admin_only = require_role("admin")     # create ONCE at module level, then reuse
```

```python
@app.delete("/links/{code}", dependencies=[Depends(admin_only)])
def remove(...): ...
```

- **Create once, reuse.** Every `require_role("admin")` call returns a *new* function object — per-request caching and (later) `dependency_overrides` match by callable identity, so two ad-hoc calls are two different dependencies.
- The class flavor is the same idea with state on `self`: `__init__(self, role)` stores the parameter, `__call__(self, x_role: ...)` is the dependency FastAPI solves.

---

## Recap & next

- ✅ `Depends` puts requirements **in the signature** — no import-time construction, no hidden coupling, substitutable in tests.
- ✅ Define each dependency once and alias it: `Settings = Annotated[AppSettings, Depends(get_settings)]`.
- ✅ Deps compose into trees (`get_link_or_404` uses `Store` + a path param) — shared logic lives once.
- ✅ Per request, each dep runs **once** (cached by callable identity); `use_cache=False` opts out.
- ✅ Classes bundle params with logic; closures/`__call__` classes parameterize a family of deps — built once at module level.
- ✅ Self-check: two sub-dependencies both declare the (future) DB-session dependency — why is per-request caching *correctness*-critical there, not just a performance win?

→ Next: **[04-2 · Yield dependencies & overrides](02_yield_dependencies_and_overrides.md)**

## Exercises

1. Write the `Pagination` class dependency with clamping (1 ≤ limit ≤ 100, offset ≥ 0) and wire it into a `GET /links` endpoint. Verify `?limit=5000` comes back clamped.

<details>
<summary>Solution</summary>

```python
class Pagination:
    def __init__(self, limit: int = 20, offset: int = 0) -> None:
        self.limit = min(max(limit, 1), 100)
        self.offset = max(offset, 0)

Page = Annotated[Pagination, Depends()]

@app.get("/links")
def list_links(page: Page):
    return {"limit": page.limit, "offset": page.offset}
```

`curl 'localhost:8000/links?limit=5000'` → `{"limit": 100, "offset": 0}`. The clamp lives in one constructor, not in every endpoint.
</details>

2. Prove per-request caching: make two sub-dependencies that both depend on `request_id`, use both in one endpoint, and confirm one uuid. Then switch one usage to `use_cache=False` and confirm two.

<details>
<summary>Solution</summary>

```python
def tag_a(rid: Annotated[str, Depends(request_id)]) -> str: return f"a-{rid}"
def tag_b(rid: Annotated[str, Depends(request_id)]) -> str: return f"b-{rid}"

@app.get("/demo")
def demo(a: Annotated[str, Depends(tag_a)], b: Annotated[str, Depends(tag_b)]):
    return {"a": a, "b": b}     # same uuid suffix — request_id ran once
```

Change `tag_b`'s inner annotation to `Depends(request_id, use_cache=False)` and the suffixes differ: the cache is opted out for that edge of the tree only.
</details>

3. Write `require_role` as a class with `__call__` instead of a closure. Why might a team prefer the class?

<details>
<summary>Solution</summary>

```python
class RequireRole:
    def __init__(self, role: str) -> None:
        self.role = role
    def __call__(self, x_role: Annotated[str, Header()] = "guest") -> None:
        if x_role != self.role:
            raise HTTPException(status_code=403, detail=f"requires role {self.role!r}")

admin_only = RequireRole("admin")
```

The class carries inspectable state (`admin_only.role` shows up in debuggers and reprs) and is easier to extend with config later; a closure's captured variables are invisible from outside. Behavior is identical.
</details>
