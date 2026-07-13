# 12 · Settings & Configuration

> **Level:** Advanced · **Prerequisites:** [11 · Authentication & JWT](11_authentication_jwt.md)
> **Time:** ~45 min · **Verified:** 2026-06-25 (pydantic-settings 2.9.1)

---

## Why this matters

Hard-coded database URLs, secret keys, and feature flags in source code are a security breach waiting to happen. Environment-specific configuration (dev vs staging vs production) belongs in environment variables, not in the repo. `pydantic-settings` reads environment variables into a typed, validated Python object — the same type hints you already know, applied to configuration.

---

## Install

```bash
pip install "pydantic-settings"
```

---

## The problem it solves

```python
# Bad — secret in code, different values per environment require code changes
DATABASE_URL = "sqlite:///./dev.db"
SECRET_KEY = "dev-only-secret"
DEBUG = True
```

```python
# Good — values come from the environment at runtime
from app.core.config import settings
settings.database_url   # read from DATABASE_URL env var
settings.secret_key     # read from SECRET_KEY env var
```

---

## `app/core/config.py`

```python
from functools import lru_cache
from pydantic import EmailStr, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "Bookstore API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"    # "development" | "staging" | "production"

    # Database
    database_url: str = "sqlite+aiosqlite:///./bookstore.db"
    db_echo: bool = False               # log SQL in dev; False in production

    # Security
    secret_key: str = "CHANGE_ME_use_secrets_token_hex_32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Optional: first admin user on fresh install
    first_superuser_email: str | None = None
    first_superuser_password: str | None = None

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if v == "CHANGE_ME_use_secrets_token_hex_32" and False:  # only in prod
            raise ValueError("SECRET_KEY must be set to a strong random value")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",           # load from .env file
        env_file_encoding="utf-8",
        case_sensitive=False,      # DATABASE_URL or database_url both work
        extra="ignore",            # ignore env vars not in Settings
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

# Module-level singleton — import this everywhere
settings = get_settings()
```

`@lru_cache` ensures `Settings()` is only constructed once per process — `.env` is read once, not on every import.

---

## `.env` file (never commit to git)

```bash
# .env
APP_NAME=Bookstore API
ENVIRONMENT=development
DEBUG=true
DB_ECHO=true

DATABASE_URL=sqlite+aiosqlite:///./bookstore.db
# Postgres alternative:
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/bookstore

SECRET_KEY=a8f3b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1
ACCESS_TOKEN_EXPIRE_MINUTES=30

ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

```bash
# .gitignore — CRITICAL
.env
*.db
__pycache__/
.venv/
```

---

## Multiple environments

```
bookstore/
├── .env               ← local development (gitignored)
├── .env.example       ← committed — shows required vars with dummy values
├── .env.test          ← test overrides (gitignored or in CI secrets)
└── app/core/config.py
```

`.env.example` — commit this so new developers know what to set:
```bash
# .env.example
APP_NAME=Bookstore API
ENVIRONMENT=development
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bookstore
SECRET_KEY=generate_with__python3_-c__import_secrets_print_secrets.token_hex_32__
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=["http://localhost:3000"]
```

For tests, override specific variables:
```python
# tests/conftest.py
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-not-used-in-production"
```

Or use a `.env.test` file:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),   # override with ENV_FILE=.env.test
    )
```

```bash
ENV_FILE=.env.test pytest
```

---

## Using settings in the app

```python
# app/main.py
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,     # hide docs in production
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

```python
# app/core/database.py
from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
)
```

---

## Production checklist

| Setting | Development | Production |
|---|---|---|
| `DEBUG` | `true` | `false` |
| `DB_ECHO` | `true` | `false` |
| `SECRET_KEY` | any string | `secrets.token_hex(32)` — never default |
| `DATABASE_URL` | SQLite file | PostgreSQL (asyncpg) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 (24h, convenient) | 15–60 |
| `ALLOWED_ORIGINS` | `*` or localhost | Your actual frontend domain(s) |
| `docs_url` / `redoc_url` | `/docs` | `None` (disable public API docs) |

---

## Common mistakes

**Committing `.env` to git:**  
Even once. Use `git rm --cached .env` to remove it from tracking. Add it to `.gitignore` before the first commit.

**`@lru_cache` with mutable default:**  
`lru_cache` caches by arguments — `get_settings()` has none, so it's called once. This is the correct pattern. Don't cache at module import time with a global (`settings = Settings()`) inside a function that can be called multiple times with different env vars — use `lru_cache`.

**Not having a `.env.example`:**  
A new team member pulls the repo, finds no `.env`, and has no idea what variables are needed. Always commit `.env.example`.

---

## Exercises

1. **Add a `log_level` setting.** Add `log_level: str = "INFO"` to `Settings`. In `main.py`, use it to configure Python's `logging` module on startup.

<details>
<summary>Solution</summary>

```python
# app/core/config.py
log_level: str = "INFO"

# app/main.py
import logging

@app.on_event("startup")
async def configure_logging():
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.db_echo else logging.WARNING
    )
```

</details>

2. **Validate `environment` values.** Add a `field_validator` that raises `ValueError` if `environment` is not one of `"development"`, `"staging"`, `"production"`.

<details>
<summary>Solution</summary>

```python
@field_validator("environment")
@classmethod
def validate_environment(cls, v: str) -> str:
    allowed = {"development", "staging", "production"}
    if v not in allowed:
        raise ValueError(f"environment must be one of {allowed}, got {v!r}")
    return v
```

</details>

---

## Recap — full section summary

You now have a complete, industry-ready FastAPI project:

| Module | What you built |
|---|---|
| 01–07 | Routes, validation, Pydantic, responses, errors, dependencies, testing |
| 08 | Flat project layout — models / schemas / crud / routers / core |
| 09 | Async SQLAlchemy — models, sessions, CRUD layer, test with in-memory DB |
| 10 | Alembic — versioned migrations, autogenerate, upgrade/downgrade |
| 11 | JWT auth — bcrypt passwords, access tokens, protected routes, ownership |
| 12 | pydantic-settings — typed env vars, .env files, environment-specific config |

**The full bookstore project** wires all of these together. Start the app:

```bash
cp .env.example .env     # fill in values
alembic upgrade head     # create tables
uvicorn app.main:app --reload
# open http://localhost:8000/docs
```

- ✅ pydantic-settings reads env vars into a typed, validated Settings object
- ✅ Never commit `.env`; always commit `.env.example`
- ✅ `@lru_cache` on `get_settings()` — reads the file once per process
- ✅ Disable `/docs` in production (`docs_url=None`); lower token expiry; use PostgreSQL
