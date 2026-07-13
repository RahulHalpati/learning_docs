# 03: Configuration & settings

> **Level:** Intermediate · **Prerequisites:** [02 · Dependency injection](02_dependency_injection.md)
> **Time:** ~1 hour · **Verified:** 2026-06-03 (FastAPI 0.136.1, pydantic-settings 2.11.0)

## Why this matters

Hardcoding a database URL or an API key in your source is the classic rookie mistake — it leaks secrets into git and means different environments (dev, staging, prod) need different code. The industry standard is **12-factor config**: read settings from the **environment**, with typed validation and sane defaults. FastAPI's companion library `pydantic-settings` makes this clean and type-safe. (You already met it indirectly — your AI project read `LLM_BACKEND` from the environment.)

## Concept: typed settings with `pydantic-settings`

`BaseSettings` is like a Pydantic model, but it **auto-populates fields from environment variables** (matching by name, case-insensitive). Define your config once, with types and defaults:

```python
# app/core/config.py
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",          # also read from a local .env file (dev convenience)
        env_prefix="",            # e.g. "APP_" would require APP_DEBUG instead of DEBUG
        extra="ignore",           # ignore unrelated env vars rather than erroring
    )

    app_name: str = "My API"
    debug: bool = False
    database_url: str = "sqlite:///./app.db"
    api_key: SecretStr = SecretStr("changeme")     # secret: hidden in logs/repr
    max_page_size: int = 100
```

What this gives you:

- Each field is read from an env var of the same name: `DEBUG`, `DATABASE_URL`, `API_KEY`, `MAX_PAGE_SIZE` (case-insensitive). Set in real environments via the shell, a container, or a secrets manager.
- **Types are enforced and coerced**: `MAX_PAGE_SIZE=50` arrives as the int `50`; `DEBUG=true` becomes the bool `True`. A bad value (e.g. `MAX_PAGE_SIZE=abc`) fails loudly at startup, not deep in a request.
- **Defaults** make every field optional for local dev while still overridable in prod.
- **`SecretStr`** wraps secrets so they don't show up in logs or `repr()` — you call `.get_secret_value()` to read the real value where you actually need it.
- **`.env` support**: in development, a local `.env` file (git-ignored!) supplies values without exporting them in your shell.

> **12-factor in one line:** code is the same everywhere; *configuration* changes per environment and comes from the environment. Never commit secrets — commit a `.env.example` with dummy values instead.

## Concept: settings as a cached dependency

You want **one** `Settings` instance for the whole app (parsing the environment repeatedly is wasteful), and you want to inject it like any other dependency. The idiom: a `@lru_cache`-d factory used with `Depends`.

```python
# app/core/config.py (continued)
from functools import lru_cache
from typing import Annotated
from fastapi import Depends


@lru_cache                          # build Settings once, reuse the same object forever
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
```
```python
# any router
@router.get("/info")
async def info(settings: SettingsDep):
    return {"app": settings.app_name, "debug": settings.debug}
```

- **`@lru_cache`** memoizes the result, so `get_settings()` builds `Settings()` on first call and returns the **same instance** every time after — effectively a singleton, without a global.
- Injecting via `Depends` (rather than importing a global) means tests can **override** `get_settings` to supply test config — same DI testability win as Module 02.

```mermaid
flowchart LR
    E["environment / .env"] --> S["Settings() (validated, typed)"]
    S --> L["@lru_cache get_settings()"]
    L -->|Depends| R1[route A]
    L -->|Depends| R2[route B]
    L -->|same instance| R3[route C]
```

## Verified: settings from the environment, injected into a route

```python
# settings_demo.py
import os

# (a real app sets these in the shell/container; we set them here to demonstrate)
os.environ["DEBUG"] = "true"
os.environ["MAX_PAGE_SIZE"] = "25"
os.environ["API_KEY"] = "super-secret-value"

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "My API"
    debug: bool = False
    max_page_size: int = 100
    api_key: SecretStr = SecretStr("changeme")


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]

app = FastAPI()

@app.get("/info")
async def info(settings: SettingsDep):
    return {
        "app": settings.app_name,            # default (no env var set)
        "debug": settings.debug,             # from DEBUG=true  -> bool True
        "max_page_size": settings.max_page_size,  # from MAX_PAGE_SIZE=25 -> int 25
        "api_key_repr": repr(settings.api_key),   # SecretStr hides the value
    }

client = TestClient(app)
print(client.get("/info").json())
# reading the real secret value where genuinely needed:
print("real secret:", get_settings().api_key.get_secret_value())
```

**Verified output:**

```
{'app': 'My API', 'debug': True, 'max_page_size': 25, 'api_key_repr': "SecretStr('**********')"}
real secret: super-secret-value
```

`DEBUG` and `MAX_PAGE_SIZE` were read from the environment and **coerced to the right types**; `app_name` fell back to its default; and the API key is masked in its `repr` (so it won't leak into logs) yet still readable via `.get_secret_value()`.

## Concept: per-environment config & `.env`

The same code runs everywhere; the environment differs:

| Environment | How config arrives |
|---|---|
| Local dev | a git-ignored `.env` file (read automatically) |
| CI/tests | env vars set by the test runner, or an overridden `get_settings` |
| Staging/Prod | env vars injected by the platform / a secrets manager (never a file in the image) |

Commit a **`.env.example`** documenting the variables with placeholder values, and add `.env` to `.gitignore`. New developers copy `.env.example` to `.env` and fill in real values.

```bash
# .env.example  (committed)
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
API_KEY=replace-me
```

## Common mistakes

**Mistake: hardcoding secrets / config in code.** `API_KEY = "sk-abc123"` in a `.py` file ends up in git history forever. Read it from the environment via `Settings`.

**Mistake: committing `.env`.** It usually holds real secrets. Git-ignore it; commit only `.env.example`.

**Mistake: a fresh `Settings()` per request.** Parsing the environment on every request is wasteful and can re-read files. Use `@lru_cache` so it's built once.

**Mistake: logging a settings object with secrets.** Plain `str` fields print in full. Wrap secrets in `SecretStr` so `print(settings)` / logs show `**********`.

**Mistake: a global `settings = Settings()` import.** It works, but injecting via `Depends(get_settings)` is more testable (overridable) and avoids import-time side effects. Prefer the dependency.

## Practice

**Exercise:** Add a `cors_origins: list[str] = []` field and set it from an env var `CORS_ORIGINS='["https://a.com","https://b.com"]'`. Confirm it parses into a Python list. (Hint: `pydantic-settings` parses JSON for complex types from env vars.)

<details><summary>Solution</summary>

```python
import os
os.environ["CORS_ORIGINS"] = '["https://a.com","https://b.com"]'

class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    cors_origins: list[str] = []

print(Settings().cors_origins)   # ['https://a.com', 'https://b.com']
```

For complex types (`list`, `dict`), `pydantic-settings` expects the env var to be **JSON**. The string `'["https://a.com","https://b.com"]'` parses into a real Python list. (Verified.) You'll feed exactly this into the CORS middleware in [Module 05](05_security_and_middleware.md).
</details>

## Recap & next

- ✅ Define config as a typed **`BaseSettings`** class; values come from **environment variables** (and an optional `.env`), validated and coerced.
- ✅ Wrap secrets in **`SecretStr`** so they don't leak into logs.
- ✅ Expose settings as a **`@lru_cache`-d dependency** (`get_settings`) and inject with `Depends` — one instance, overridable in tests.
- ✅ Never commit secrets; commit a `.env.example`. Same code, per-environment config = 12-factor.
- Self-check: why inject `get_settings` via `Depends` instead of importing a global `settings`?

→ Next: **[04 · Errors, status codes & response design](04_errors_and_responses.md)** — what your responses should look like.
