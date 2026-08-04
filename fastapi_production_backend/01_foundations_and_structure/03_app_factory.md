# 01-3 · The app factory

> **Level:** Intermediate · **Prerequisites:** [01-2 · Config & settings](02_config_and_settings.md)
> **Time:** 25 min · **Verified:** 2026-07-27 (fastapi 0.140.8)

## Why this matters

Where does the `FastAPI()` instance get created, and where do middleware, routers, and error handlers get attached? Scattering that across imports makes the app hard to test and reason about. The **application factory** — a `create_app()` function — assembles everything in *one* place, so you can build a fresh, fully-wired app on demand (including in tests).

---

## `create_app()`

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.observability.metrics import setup_metrics
from app.observability.middleware import RequestContextMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()                 # startup
    yield
    # shutdown: dispose pools, close clients, etc.

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(RequestContextMiddleware)     # request id + access log

    register_exception_handlers(app)                 # domain errors → clean JSON
    setup_metrics(app)                               # /metrics for Prometheus
    app.include_router(api_router)                   # all of /api/v1
    return app

app = create_app()
```

Read it top to bottom and you see the *entire* shape of the app: what it's called, what runs at startup/shutdown, what middleware wraps requests, how errors are handled, and which routers are mounted. Nothing is hidden in a side-import.

---

## Why a factory (not a module-level `app` with scattered wiring)?

- **Testability:** tests can build a fresh app (or reuse this one) and override dependencies cleanly (Section 06). A factory makes "give me a configured app" a function call.
- **One source of truth:** middleware order, handler registration, and router mounting all live here — no hunting.
- **Explicit lifespan:** startup/shutdown logic (logging config, warming caches, disposing pools) has an obvious home.

`app = create_app()` at the bottom is what `uvicorn app.main:app` imports.

---

## Lifespan: startup & shutdown

The `lifespan` async context manager runs code **once** at startup (before `yield`) and **once** at shutdown (after). Use it for process-wide setup: configure logging, create shared clients/pools, and tear them down cleanly. (It replaced the old `@app.on_event("startup")` hooks.)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # e.g. app.state.http = httpx.AsyncClient()
    yield
    # await app.state.http.aclose()
```

---

## The routers plug in here

Each feature's routes live in `api/v1/`, and a single aggregator wires them under `/api/v1`:

```python
# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1 import auth, health, projects, tasks

api_router = APIRouter(prefix="/api/v1")
for module in (health, auth, projects, tasks):
    api_router.include_router(module.router)
```

The factory includes just `api_router` — adding a feature is one line here, not a change to `main.py`. (Routers and versioning get their own treatment in [05-1](../05_api_design_and_robustness/01_routers_and_versioning.md).)

> **Tip — middleware order matters.** Middleware wraps in the order added and executes outermost-first. Put cross-cutting concerns that should see *every* request (request-id, metrics) early. We'll revisit this in [05-3](../05_api_design_and_robustness/03_middleware_and_cors.md).

---

## Recap & next

- ✅ `create_app()` assembles the app in one place: lifespan, middleware, handlers, routers.
- ✅ A factory makes the app **testable** (build/override on demand) and its shape **obvious**.
- ✅ **Lifespan** owns startup/shutdown; a router **aggregator** mounts all features under `/api/v1`.
- ✅ `app = create_app()` is what `uvicorn app.main:app` runs.
- ✅ Self-check: why is a `create_app()` function easier to test than a bare module-level `app` with wiring spread across imports?

→ Next: **[02 · Data layer](../02_data_layer/README.md)**

## Exercises

1. Add a startup log line in `lifespan` that prints the environment and database backend (`settings.environment`, and whether the URL starts with `sqlite`/`postgresql`).

<details>
<summary>Solution</summary>

In `lifespan`, after `configure_logging()`, `logging.getLogger("taskflow").info(f"starting in {settings.environment} on {settings.database_url.split('://')[0]}")`. You'll see it once at boot — a cheap, useful "what am I running as?" signal in the logs.
</details>
