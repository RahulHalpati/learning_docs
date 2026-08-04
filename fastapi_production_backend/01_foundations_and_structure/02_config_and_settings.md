# 01-2 · Config & settings

> **Level:** Intermediate · **Prerequisites:** [01-1 · Project layout](01_project_layout.md)
> **Time:** 25 min · **Verified:** 2026-07-27 (pydantic-settings 2.14.2)

## Why this matters

Configuration that differs between dev, staging, and production — database URLs, secrets, feature flags — must come from the **environment**, never be hard-coded. That's the [12-factor](https://12factor.net/config) principle, and it's what lets the *same* image run safely in every environment. `pydantic-settings` gives you typed, validated config from env vars and `.env` files.

---

## Typed settings from the environment

```python
# app/core/config.py
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TaskFlow"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./taskflow.db"   # SQLite by default
    jwt_secret: str = "dev-secret-change-me-in-production-0123456789"
    access_token_expire_minutes: int = 30
    redis_url: str = "redis://localhost:6379"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

@lru_cache
def get_settings() -> Settings:      # parse once, reuse everywhere
    return Settings()

settings = get_settings()
```

Each field is **typed** — Pydantic parses and validates env values (a non-integer `ACCESS_TOKEN_EXPIRE_MINUTES` fails fast at startup, not at request time). Field names map to env vars **case-insensitively**: `database_url` ← `DATABASE_URL`.

```python
from app.core.config import settings
print(settings.app_name, settings.environment, settings.database_url)
```

**Output (real run, defaults):**
```
TaskFlow | development | sqlite+aiosqlite:///./taskflow.db
```

Override from the environment — no code change:

**Output (real run, `DATABASE_URL=... ENVIRONMENT=production`):**
```
production | postgresql+asyncpg://u:p@db/taskflow
```

That's the whole point: **one build, many environments.** The SQLite default means the app runs offline with zero setup; production sets `DATABASE_URL` to Postgres.

---

## The `.env` file (local only)

For local dev, put overrides in a `.env` file (loaded automatically) — and **never commit it** (it holds secrets). Ship a `.env.example` instead:

```bash
# .env.example  (copy to .env)
DATABASE_URL=sqlite+aiosqlite:///./taskflow.db
JWT_SECRET=dev-secret-change-me-in-production-0123456789
REDIS_URL=redis://localhost:6379
```

Precedence: real environment variables **override** `.env`, which overrides the field defaults. In production you set real env vars (via your platform / Secret Manager) and don't ship a `.env` at all.

> ⚠️ **Secrets are config too — and the riskiest kind.** `JWT_SECRET`, DB passwords, API keys must come from the environment, never the repo. Generate a real JWT secret with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and set it per environment. A leaked secret in git history is a breach.

---

## Why `@lru_cache`?

`get_settings()` is cached so the `.env` file is parsed **once** per process, not on every import or request. `settings` is effectively a singleton. (In tests you can override it via dependency injection — Section 06.)

---

## Recap & next

- ✅ Load config from the environment with `pydantic-settings` — typed, validated, 12-factor.
- ✅ Defaults make it run offline; env vars (or `.env`) override per environment — **one build, many envs**.
- ✅ Secrets come from the environment only; commit `.env.example`, never `.env`.
- ✅ `@lru_cache` makes settings a parse-once singleton.
- ✅ Self-check: where should the production database password live, and where must it *never* live?

→ Next: **[01-3 · The app factory](03_app_factory.md)**

## Exercises

1. Add a `debug: bool = False` setting and make the SQLAlchemy engine's `echo` follow it (SQL logging on when `DEBUG=true`).

<details>
<summary>Solution</summary>

Add `debug: bool = False` to `Settings`; in `db/session.py`, `create_async_engine(settings.database_url, echo=settings.debug)`. Now `DEBUG=true uvicorn app.main:app` logs every SQL statement — handy locally, off in production.
</details>
