# 04-3 · App factory & routers

> **Level:** Beginner→Intermediate · **Prerequisites:** [04-2 · Yield dependencies & overrides](02_yield_dependencies_and_overrides.md)
> **Time:** ~40 min · **Verified:** 2026-08-07 (FastAPI 0.116 · Pydantic 2.11)

## Why this matters

`app = FastAPI()` at module level means your application is a *side effect of an import* — built exactly once, with exactly one configuration, before any test gets a say. A factory (`create_app()`) makes construction an explicit, repeatable call, and `APIRouter` lets the app be assembled from resource-sized pieces instead of one growing file. Together they're the skeleton every production FastAPI service hangs on.

---

## Why module-level `app` fights you

```python
# app/main.py — the tutorial way
from fastapi import FastAPI
from app.core.config import AppSettings

settings = AppSettings()                 # env must be perfect just to IMPORT this
app = FastAPI(debug=settings.debug)      # built at import time, config frozen

@app.get("/health")                      # every route in one ever-growing file
def health(): ...
```

- **One config per process.** Want to test the app with `debug=True` *and* `debug=False`? You can't — there is only ever the one `app`, configured at import.
- **Import side effects.** Importing this module to test one helper constructs settings (and later, engines and clients). Tests get slow and env-dependent for no reason.
- **A magnet for circular imports.** Everything registers on `app`, so everything imports `main`, and `main` imports everything.

---

## The factory

Construction becomes a function; configuration becomes its argument:

```python
# app/main.py
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI
from app.api import health, links
from app.core.config import AppSettings, get_settings

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # startup: open what the PROCESS owns — Section 05 puts the DB engine here
    yield
    # shutdown: close it — runs on Ctrl-C and clean worker exit

def create_app(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)   # lifespan, never on_event
    app.dependency_overrides[get_settings] = lambda: settings   # every dep sees THESE settings
    app.include_router(health.router)
    app.include_router(links.router, prefix="/api/v1")
    return app
```

Run it with uvicorn's factory mode — no module-level instance anywhere:

```bash
uv run uvicorn 'app.main:create_app' --factory --reload
```

- **Two apps, two configs, one process** — the thing globals made impossible:
  `create_app(AppSettings(debug=True))` and `create_app(AppSettings(debug=False))` coexist happily in one test run.
- The `dependency_overrides[get_settings]` line is the injection trick: whatever settings the factory received, that's what every `Settings`-typed dependency resolves to. No global to patch, ever.
- `lifespan` replaces the deprecated `@app.on_event("startup"/"shutdown")` — it's one context manager, so setup and teardown can share local variables.

---

## APIRouter: one file per resource

A router is a mountable slice of the app — same decorators, no app required:

```python
# app/api/links.py
from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse
from app.api.deps import CurrentLink, Store
from app.schemas.links import LinkIn, LinkOut

router = APIRouter(prefix="/links", tags=["links"])   # tags group these in /docs

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_link(payload: LinkIn, store: Store) -> LinkOut:
    return store.add(payload.url)

@router.get("/{code}")
async def resolve(link: CurrentLink) -> RedirectResponse:
    return RedirectResponse(link.url)                 # 307 by default
```

```python
# app/api/health.py
from fastapi import APIRouter

router = APIRouter(tags=["ops"])

@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

Routers import *dependencies and schemas* — never `main`. That single direction of imports is what kills circular-import bugs before they exist.

---

## Composition and versioning

`include_router` is where prefixes stack and cross-cutting concerns attach:

```python
app.include_router(health.router)                       # /health — ops probes stay unversioned
app.include_router(links.router, prefix="/api/v1")      # /api/v1/links, /api/v1/links/{code}
```

- **Prefixes stack**: the composer's `/api/v1` + the router's `/links` = `/api/v1/links`. The router file never hard-codes the version — when `/api/v2` arrives, include the new router under a new prefix and v1 clients are untouched.
- `include_router` also accepts `dependencies=[...]` and `tags=[...]` — the *composer* decides which slices get guarded (that's how the gate protects mutating routes only).
- Prefix rules: never ends with `/`; use path `""` for the collection root (`POST /links`, not `POST /links/`).

---

## Directory structure for a growing service

```
app/
├── main.py              # create_app() + lifespan — the ONLY place FastAPI() is called
├── core/
│   └── config.py        # AppSettings + get_settings (pydantic-settings)
├── api/
│   ├── deps.py          # Annotated aliases: Settings, Store, CurrentLink
│   ├── health.py        # APIRouter — ops endpoints
│   └── links.py         # APIRouter — one file per resource
├── schemas/
│   └── links.py         # Pydantic request/response models
└── stores/
    └── memory.py        # InMemoryLinkStore (a DB replaces this in Section 05)
```

The rule that keeps it healthy: **`api/` imports from `deps`/`schemas`/`stores`; nothing imports `main`.** New resource = new `api/<resource>.py` + `schemas/<resource>.py` + one `include_router` line. The structure grows linearly, not combinatorially.

---

## Lifespan inside the factory

When startup needs configuration, define `lifespan` *inside* `create_app` so it closes over the settings:

```python
import httpx

def create_app(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.http = httpx.AsyncClient(timeout=settings.http_timeout)  # settings in scope
        yield
        await app.state.http.aclose()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    ...
```

Module-level `lifespan` is fine while it needs no config; move it into the factory the day it does. Either way each `create_app()` call gets its own resources — two test apps never share a client or a pool by accident.

---

## Recap & next

- ✅ Module-level `app = FastAPI()` = import side effects + one frozen config; **`create_app(settings)`** makes construction explicit and repeatable.
- ✅ Inject the factory's settings with `app.dependency_overrides[get_settings] = lambda: settings` — no module global anywhere.
- ✅ One `APIRouter` per resource, with `prefix` and `tags`; routers never import `main`.
- ✅ Version at composition time (`include_router(..., prefix="/api/v1")`), not inside router files.
- ✅ `lifespan` (not `on_event`) owns process-level resources; move it inside the factory when it needs settings.
- ✅ Self-check: why does versioning belong in `include_router` rather than in each router's own `prefix`?

Now build the section's mini-project and gate — see the [section README](README.md).

→ Next: **[Section 05 · Async database: SQLAlchemy & Alembic](../05_async_database_sqlalchemy_alembic/README.md)**

## Exercises

1. Prove the multi-config win: build two apps with different settings in one script and assert `/info` differs, using `httpx.ASGITransport`.

<details>
<summary>Solution</summary>

```python
import asyncio, httpx
from app.main import create_app
from app.core.config import AppSettings

async def probe(app) -> bool:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as c:
        return (await c.get("/info")).json()["debug"]

async def main() -> None:
    on = create_app(AppSettings(debug=True))
    off = create_app(AppSettings(debug=False))
    assert await probe(on) is True and await probe(off) is False

asyncio.run(main())
```

With a module-level `app`, the second configuration literally cannot exist in the same process — this script *is* the argument for the factory.
</details>

2. Move the links router to `/api/v2` while keeping `/api/v1` serving. How many lines change, and in which file?

<details>
<summary>Solution</summary>

Two lines, both in `app/main.py`:

```python
app.include_router(links.router, prefix="/api/v1")   # keep v1 clients working
app.include_router(links_v2.router, prefix="/api/v2")
```

`links.py` doesn't change at all — because the version was never written inside it. That's the payoff of versioning at composition time.
</details>

3. You need a rate-limit check on every `/api/v1` endpoint but not on `/health`. Where does it go?

<details>
<summary>Solution</summary>

At composition time, on the versioned include only:

```python
app.include_router(links.router, prefix="/api/v1",
                   dependencies=[Depends(rate_limit)])
app.include_router(health.router)          # probes stay cheap and unguarded
```

Not app-wide (`FastAPI(dependencies=...)` would throttle health probes) and not per-endpoint (N copies of the same guard). The composer owns cross-cutting policy.
</details>
