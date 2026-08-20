# 02-3 · Response models, settings & lifespan

> **Level:** Beginner · **Prerequisites:** [02-2 · Pydantic v2 deep dive](02_pydantic_v2_deep_dive.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (FastAPI 0.116 · Pydantic 2.11 · pydantic-settings 2.x)

## Why this matters

Input validation keeps garbage *out*; this lesson is about the other three edges of a production app. **Response models** control what leaves your API — an output filter is a security boundary, not a convenience. **pydantic-settings** moves config out of code and into the environment, so the same image runs in dev and prod. And **lifespan** is the one correct place to acquire and release process-wide resources — the deprecated `@app.on_event` got this wrong, and you'll see exactly why.

---

## `response_model`: output filtering is a security boundary

Whatever your function returns goes over the wire — *unless* you declare a response model. Consider the difference:

```python
from pydantic import BaseModel

class UserOut(BaseModel):
    id: int
    username: str

FAKE_DB = {
    1: {"id": 1, "username": "ada",
        "hashed_password": "$2b$12$...", "owner_email": "ada@corp.internal"},
}

@app.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: int):
    return FAKE_DB[user_id]        # raw internal record — but only id + username leave
```

With `response_model=UserOut`, FastAPI validates and **filters** the return value: `hashed_password` and `owner_email` are stripped, and `/docs` documents exactly `{id, username}`. Without it, the raw dict — secrets and all — ships to the client.

Why treat this as a security boundary and not a nicety:

- **Internal objects grow.** Someone adds `is_admin` or `stripe_customer_id` to the record next quarter. With a response model, nothing changes at the API edge. Without one, the new field leaks the day it's added — the worst kind of bug, because nothing *breaks*.
- **Never return ORM/internal objects raw.** The database row is your private representation; the response model is your public contract. Keeping them separate is what lets each evolve independently.

You can also declare it as the **return annotation** — same effect, and type checkers see it too:

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int) -> UserOut:      # annotation acts as response_model
    return FAKE_DB[user_id]
```

Use `response_model=` when the annotation can't express it (e.g. you return a raw dict for performance) — but one of the two must always be there on anything returning domain data.

---

## Separate In and Out schemas

Input and output are different contracts, so they get different models — the classic case is passwords:

```python
class UserIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=12)      # arrives on input…

class UserOut(BaseModel):
    id: int
    username: str                             # …and never appears on output

@app.post("/users", response_model=UserOut, status_code=201)
async def create_user(payload: UserIn):
    user = {"id": 1, "username": payload.username,
            "hashed_password": hash_it(payload.password)}
    return user                               # UserOut filters the hash out
```

Resist the "one `User` model for everything" shortcut: it forces `password` to be optional (breaking input validation) *and* risks echoing it back (breaking output filtering). Two small models beat one wrong one. Naming convention for the course: `XCreate`/`XIn` for input, `XOut` for output.

`status_code` completes the contract: `201` for creation, and for deletes:

```python
from fastapi import status

@app.delete("/links/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(slug: str) -> None:
    ...                                        # 204 = success, no body — return nothing
```

The `status` constants read better in review than bare integers, and the declared code flows straight into `/docs`.

---

## Settings: pydantic-settings + `.env`

Hard-coded config is a deploy blocker — the base URL differs between your laptop and prod, and secrets must never live in git. **pydantic-settings** reads config from the environment with full Pydantic validation:

```bash
uv add pydantic-settings
```

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",              # fall back to a local .env file
        env_prefix="LINKBOX_",        # only read LINKBOX_* vars — no collisions
    )
    base_url: str = "http://127.0.0.1:8000"
    slug_length: int = 6
    debug: bool = False
```

```bash
# .env — local values; add .env to .gitignore, commit a .env.example instead
LINKBOX_BASE_URL=http://127.0.0.1:8000
LINKBOX_SLUG_LENGTH=8
LINKBOX_DEBUG=true
```

- Precedence: real environment variables **beat** `.env`, which beats the field defaults — so prod (where env vars come from the platform, not a file) just works.
- Values are *validated*: `LINKBOX_SLUG_LENGTH=banana` fails at startup with a clear error, not at request time three hours later. Fail fast on misconfiguration.
- `SettingsConfigDict` is `ConfigDict` plus settings-specific options — same v2 pattern you already know.

### One instance, injected

Construct `Settings()` once (it reads files and the environment — don't repeat that per request) and expose it as a dependency:

```python
# config.py (continued)
from functools import lru_cache

@lru_cache                        # first call builds it; every later call returns the same object
def get_settings() -> Settings:
    return Settings()
```

```python
from typing import Annotated
from fastapi import Depends

@app.get("/info")
async def info(settings: Annotated[Settings, Depends(get_settings)]) -> dict:
    return {"base_url": settings.base_url, "slug_length": settings.slug_length}
```

Why `Depends` instead of importing a global `settings = Settings()`? **Overridability** — in tests you'll swap `get_settings` for one that returns test config, without monkeypatching modules. This is your first taste of dependency injection; Section 04 is entirely about it.

---

## Lifespan: startup & shutdown done right

Process-wide resources — HTTP client pools, DB engines, caches, even our in-memory link store — must be created **once at startup** and released **at shutdown**. The modern contract is a single async context manager:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup: runs once, before the first request ----
    settings = get_settings()
    app.state.links = {}                       # the linkbox store lives here
    print(f"linkbox ready → {settings.base_url} (slugs: {settings.slug_length} chars)")
    yield                                      # ← the app serves requests here
    # ---- shutdown: runs once, after the last request ----
    app.state.links.clear()
    print("linkbox shutting down")

app = FastAPI(title="linkbox", lifespan=lifespan)
```

Everything before `yield` is startup; everything after is shutdown. State hangs off `app.state`, reachable in endpoints via `request.app.state.links`.

### Why `@app.on_event` is deprecated — don't use it

Old tutorials show this; **it is deprecated** and you should flag it in any codebase you touch:

```python
@app.on_event("startup")       # ❌ deprecated — never write this
async def startup(): ...

@app.on_event("shutdown")      # ❌ deprecated
async def shutdown(): ...
```

The design was broken in two ways that lifespan fixes:

- **No resource pairing.** Startup and shutdown were separate functions, so the thing you opened in one wasn't in scope in the other — you smuggled it through a global and hoped both sides stayed in sync. In `lifespan`, acquire and release share one function body: a local variable created before `yield` is right there after it. It's the same guarantee `with open(...)` gives you, applied to the whole app.
- **No reliable ordering.** With multiple independent handlers, the acquire/release ordering across them was implicit and fragile. One lifespan function makes order explicit — and nesting `async with` inside it releases resources in exact reverse order of acquisition, automatically.

If you need both a v2 mental model and a smoke test: run the app, and the banner printing before the first request proves startup; `Ctrl+C` printing the shutdown line proves pairing.

---

## Recap & next

- ✅ `response_model` (or the return annotation) **filters output** — a security boundary. Never return ORM/internal objects without one.
- ✅ Separate `In`/`Out` schemas: password in, never out; internal fields never leak, even as the internal shape grows.
- ✅ `status_code=` declares the success code (`201` create, `204` delete-no-body) into code *and* docs.
- ✅ `BaseSettings` + `SettingsConfigDict(env_file=".env")` = validated config; env beats `.env` beats defaults; fail fast on bad values.
- ✅ `@lru_cache` + `Depends(get_settings)` = one settings instance, swappable in tests.
- ✅ Lifespan = one `@asynccontextmanager` passed to `FastAPI(lifespan=...)`; `@app.on_event` is deprecated (no pairing, no ordering).
- ✅ Self-check: your teammate adds `is_admin` to the user record dict. Which of the two apps above leaks it — and why does the other one not even need a code change?

→ Next: **[Section 03 · Request handling: forms, files & parsing](../03_request_handling_files_parsing/README.md)**

## Exercises

1. Write `POST /links` with separate schemas: `LinkIn` (`url: HttpUrl`, optional constrained `slug`) and `LinkOut` (`slug`, `url` — but the stored record also has `created_by_ip`). Prove via `/docs` and a real request that `created_by_ip` never leaves.

<details>
<summary>Solution</summary>

```python
class LinkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: HttpUrl
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9-]{3,30}$")

class LinkOut(BaseModel):
    slug: str
    url: str

@app.post("/links", response_model=LinkOut, status_code=201)
async def create_link(payload: LinkIn):
    record = {"slug": payload.slug or "gen123", "url": str(payload.url),
              "created_by_ip": "203.0.113.7"}          # internal-only field
    return record
```

`/docs` shows the 201 response schema as `{slug, url}` only, and the live response omits `created_by_ip` — `response_model` filtered it. Note `str(payload.url)`: `HttpUrl` is a rich object, so convert before storing.
</details>

2. Add a `log_level: str` setting that only accepts `"debug"`, `"info"`, or `"warning"`. Set `LINKBOX_LOG_LEVEL=verbose` in `.env` and start the app. What happens, and why is that the behavior you want?

<details>
<summary>Solution</summary>

```python
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LINKBOX_")
    log_level: Literal["debug", "info", "warning"] = "info"
```

The app **fails at startup** with a ValidationError naming `log_level` and the allowed values. That's exactly right: a typo'd config value should kill the deploy immediately and loudly — not boot a service that silently logs at the wrong level for a week.
</details>

3. Take an app that uses `@app.on_event("startup")` to create `app.state.store = {}` and `@app.on_event("shutdown")` to clear it. Migrate it to lifespan, and state the one-sentence reason the new version is safer.

<details>
<summary>Solution</summary>

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = {}
    yield
    app.state.store.clear()

app = FastAPI(lifespan=lifespan)
```

Safer because acquisition and release now live in one function body around a single `yield` — the pairing is structural (like a `with` block), instead of two disconnected handlers that only stay consistent by discipline.
</details>
