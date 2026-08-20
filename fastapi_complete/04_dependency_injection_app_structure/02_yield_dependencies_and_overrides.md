# 04-2 · Yield dependencies & overrides

> **Level:** Beginner→Intermediate · **Prerequisites:** [04-1 · Depends fundamentals](01_depends_fundamentals.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (FastAPI 0.116 · Pydantic 2.11)

## Why this matters

Most real dependencies aren't values — they're **resources**: connections, sessions, file handles, things that must be *acquired before* the request and *released after it*, even when the endpoint blows up. A `yield` dependency is FastAPI's resource manager: setup above the `yield`, the request runs at the `yield`, teardown below it. And because every dependency is a named seam, `app.dependency_overrides` can replace any of them wholesale — which is why DI-heavy apps are the easy ones to test.

---

## yield = setup → use → teardown

Replace `return` with `yield` and the dependency becomes a generator FastAPI drives around the request:

```python
from collections.abc import AsyncIterator

async def get_store_session(settings: Settings) -> AsyncIterator[LinkStore]:
    store = await connect_store(settings.store_url)   # SETUP — before the endpoint
    try:
        yield store                                    # endpoint runs here, using `store`
    finally:
        await store.close()                            # TEARDOWN — success OR failure
```

- The value at `yield` is what the endpoint receives — exactly like `return`, but the function stays alive.
- `finally` guarantees release: a raised exception, a validation failure downstream, a cancelled client — the resource is still closed. Skip the `try/finally` and every error leaks a connection.
- This is the shape of the `get_db` session dependency you'll build in [Section 05](../05_async_database_sqlalchemy_alembic/README.md) — one session per request, cleaned up unconditionally.

---

## Exceptions around the yield

When the endpoint (or any deeper dependency) raises, the exception is thrown **into the generator at the `yield`**. That makes the dependency the natural place to react to the request's outcome:

```python
async def get_session() -> AsyncIterator[Session]:
    session = acquire()
    try:
        yield session
        await session.commit()        # reached ONLY if the endpoint returned normally
    except Exception:
        await session.rollback()      # the endpoint's exception surfaces HERE
        raise                         # ALWAYS re-raise — see below
    finally:
        await session.close()         # unconditional cleanup, both paths
```

Two rules that prevent 3am pages:

- **Always re-raise.** Swallow the exception and FastAPI has no endpoint result *and* no error to handle — the client gets a bare 500 and your exception handlers never run. `except` here means "react" (rollback, log), never "handle".
- **Teardown can't rewrite the response.** Code after `yield` runs after the response has gone out — a failure there belongs in the logs, not in a new `HTTPException`. Decide the client-visible outcome *at or before* the yield.

---

## Teardown timing: streaming and background tasks

The teardown doesn't run when the endpoint *returns* — it runs when the **response is finished sending**. That ordering is deliberate:

```python
from fastapi.responses import StreamingResponse

@app.get("/export")
async def export(store: Store) -> StreamingResponse:
    async def rows() -> AsyncIterator[bytes]:
        async for link in store.iter_all():          # store is STILL OPEN while streaming
            yield f"{link.code},{link.url}\n".encode()
    return StreamingResponse(rows(), media_type="text/csv")
```

- The endpoint returns immediately with a *generator*; the body is produced while it's being sent. A `with`-block inside the endpoint would already be closed by then — the yield dependency outlives the response body precisely so streaming can keep using the resource.
- **Background tasks are the flip side** (FastAPI 0.106+): they run *after* teardown, so they must not use yielded resources. A background task that needs a session acquires its own.

---

## dependency_overrides: the swap switch

Every dependency is keyed by its callable. `app.dependency_overrides` is a plain dict that says "when solving *this* callable, call *that* one instead":

```python
# swap_demo.py — prove storage is swappable without touching app code
import asyncio, httpx
from app.main import create_app
from app.api.deps import get_store
from app.stores.memory import InMemoryLinkStore

async def main() -> None:
    app = create_app()
    fake = InMemoryLinkStore(seed={"abc123": "https://example.com"})
    app.dependency_overrides[get_store] = lambda: fake        # key = the ORIGINAL callable
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/api/v1/links/abc123", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "https://example.com"
    print("override works")

asyncio.run(main())
```

Mechanics worth memorizing:

- **The key is the original function object** — not its name, not the alias. (This is why parameterized deps must be created once at module level: an ad-hoc `require_role("admin")` can't be matched.)
- The replacement is any FastAPI-solvable callable — a lambda, a function with its own deps, even another yield dependency.
- It applies **everywhere** that dep appears, at any depth of the tree — override `get_store` once and the endpoint, `get_link_or_404`, and anything else all get the fake.
- Reset with `app.dependency_overrides.clear()` when the test is done.

This is the backbone of testing FastAPI apps — no network, no monkeypatching, no test doubles smuggled through imports. Section 09 builds the full pytest workflow on top of it.

---

## Router- and app-level dependencies

Cross-cutting checks — auth, rate limits — shouldn't be repeated in every signature. Attach them to a router (or the whole app) with `dependencies=[...]`:

```python
from fastapi import APIRouter, Depends, Header, HTTPException

def verify_client(x_client_id: Annotated[str | None, Header()] = None) -> None:
    if x_client_id is None:
        raise HTTPException(status_code=400, detail="X-Client-Id header required")

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verify_client)],   # runs for EVERY route below
)

# or app-wide:            FastAPI(dependencies=[Depends(verify_client)])
# or at composition time: app.include_router(router, dependencies=[Depends(verify_client)])
```

- **Return values are discarded** — these deps work by side effect: raise to reject, return to pass. Perfect for guards, wrong for providing data.
- The `include_router(..., dependencies=[...])` form lets the *composer* decide which routers get guarded — exactly what the section gate uses to protect mutating routes while leaving GET redirects public.
- They're still ordinary dependencies: per-request cached, and overridable — `app.dependency_overrides[verify_client] = lambda: None` turns the guard off for a test.

---

## Recap & next

- ✅ `yield` deps: **setup → yield → teardown**; `try/finally` makes release unconditional.
- ✅ Endpoint exceptions surface **at the yield** — react (`rollback`, log) and **always re-raise**; teardown runs after the response and can't change it.
- ✅ Yielded resources outlive the response *body* — that's what makes streaming from a session possible; background tasks run after teardown and must not touch it.
- ✅ `app.dependency_overrides[original_callable] = replacement` swaps a dep everywhere, at any depth — the backbone of testing (full treatment in Section 09).
- ✅ `dependencies=[Depends(...)]` on a router/app/include_router = cross-cutting guards, return values discarded.
- ✅ Self-check: why must a background task acquire its own session instead of reusing the request's yielded one?

→ Next: **[04-3 · App factory & routers](03_app_factory_and_routers.md)**

## Exercises

1. Write a `timed` yield dependency that logs the request's duration — including for requests that raise.

<details>
<summary>Solution</summary>

```python
import time, logging
from collections.abc import Iterator

def timed() -> Iterator[None]:
    t0 = time.perf_counter()
    try:
        yield
    finally:
        logging.info("request took %.1f ms", (time.perf_counter() - t0) * 1000)

app = FastAPI(dependencies=[Depends(timed)])
```

`finally` (not code after a bare yield) is what makes failed requests get timed too. Yielding `None` is fine — guards and observers don't have to provide a value.
</details>

2. Break the rules on purpose: in a yield dependency, catch `Exception` around the yield and *don't* re-raise. Hit an endpoint that raises `HTTPException(404)`. What does the client see, and why?

<details>
<summary>Solution</summary>

The client gets a **500 Internal Server Error** — not the 404. The dependency swallowed the exception, so FastAPI's exception handlers never saw the `HTTPException`, yet there's no return value to build a response from either. Add `raise` back and the 404 flows to the handler as designed. Moral: `except` in a yield dep observes, it never handles.
</details>

3. Write a 10-line script that overrides `get_settings` to force `debug=True` and verifies it through a `/info` endpoint via `httpx.ASGITransport`.

<details>
<summary>Solution</summary>

```python
import asyncio, httpx
from app.main import create_app
from app.core.config import AppSettings, get_settings

app = create_app()
app.dependency_overrides[get_settings] = lambda: AppSettings(debug=True)

async def main() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/info")).json()["debug"] is True

asyncio.run(main())
```

No env vars touched, no reload — the override wins because endpoints ask for settings *through the dependency*, never via a module global.
</details>
