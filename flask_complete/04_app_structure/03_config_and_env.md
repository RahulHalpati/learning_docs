# 04-3 · Config & environments

> **Level:** Intermediate · **Prerequisites:** [04-1 · The application factory](01_app_factory.md)
> **Time:** 35 min · **Verified:** 2026-07-29 (Flask 3.1.3)

## Why this matters

Your app needs different settings in development, testing, and production — different databases, debug on/off, different secrets. Hard-coding them means editing code to deploy (and eventually committing a production password). The industry pattern is **config classes + environment variables**.

---

## Config classes

```python
# app/config.py
class Config:
    """Defaults shared by every environment."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///flasknotes.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"          # in-memory: fast + isolated

class ProductionConfig(Config):
    DEBUG = False
    def __init__(self):
        if self.SECRET_KEY == "dev-secret-change-me-in-production":
            raise RuntimeError("SECRET_KEY must be set in production")   # fail fast

config_by_name = {"development": DevelopmentConfig,
                  "testing": TestingConfig,
                  "production": ProductionConfig}
```

Inheritance means shared defaults live once. That `ProductionConfig.__init__` guard is worth copying: it makes booting production with the dev secret **impossible** rather than merely inadvisable.

Load it in the factory:

```python
app.config.from_object(config_by_name[config_name]())
app.config.from_prefixed_env()          # any FLASK_* env var overrides
```

`from_prefixed_env()` (Flask 2.2+) maps `FLASK_SECRET_KEY` → `SECRET_KEY`, and parses JSON values — so `FLASK_MAX_CONTENT_LENGTH=1000000` arrives as an int.

---

## Reading config

```python
from flask import current_app
current_app.config["UPLOAD_FOLDER"]        # in a blueprint/view
app.config["SECRET_KEY"]                    # where you have `app`
```

`app.config` is a dict; `current_app.config` is how blueprint code reads it without importing the app object.

---

## Secrets

```bash
# .env  (git-ignored!)   — commit a .env.example instead
FLASK_ENV=production
SECRET_KEY=a-long-random-string
DATABASE_URL=postgresql+psycopg://user:pass@db:5432/flasknotes
```

Generate a real key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ **`SECRET_KEY` signs the session cookie.** If it leaks, anyone can forge a session and log in as any user. Keep it out of git (`.gitignore` your `.env`), give each environment its own, and rotate it if exposed — rotating logs everyone out, which is the correct trade. In production, inject it from your platform's secret store rather than a file.

---

## The three environments

| Env | `DEBUG` | Database | Server |
|-----|:-------:|----------|--------|
| development | ✅ | local SQLite | `flask run --debug` |
| testing | ❌ | `sqlite://` (in-memory) | pytest |
| production | ❌ **never on** | Postgres | gunicorn |

`DEBUG=True` in production exposes an interactive debugger — remote code execution for anyone who can trigger an error. The `ProductionConfig` above sets it `False` and refuses to start on a default secret; those two lines prevent the two worst config mistakes.

> **Tip — the instance folder.** `Flask(__name__, instance_relative_config=True)` enables an `instance/` directory (git-ignored by convention) for per-deployment files: a local SQLite database, a `config.py` with real secrets. Handy for single-server deployments.

---

## Recap & next

- ✅ **Config classes** (`Config` → `Development`/`Testing`/`Production`) share defaults via inheritance.
- ✅ `from_object(...)` + **`from_prefixed_env()`** lets `FLASK_*` env vars override — one build, many environments.
- ✅ Make production **fail fast** on a default `SECRET_KEY`; never `DEBUG=True` in production.
- ✅ Secrets come from the environment; commit `.env.example`, never `.env`.
- ✅ Self-check: what can an attacker do with a leaked `SECRET_KEY`?

→ Next: **[05 · Data layer](../05_data_layer/README.md)**

## Exercises

1. Add a `StagingConfig` that inherits production behavior but points at a staging database, and select it with `FLASK_ENV=staging`.

<details>
<summary>Solution</summary>

```python
class StagingConfig(ProductionConfig):
    SQLALCHEMY_DATABASE_URI = os.environ.get("STAGING_DATABASE_URL", ...)
config_by_name["staging"] = StagingConfig
```
It inherits the production safety checks (no debug, secret required) while overriding just the database — the point of the class hierarchy.
</details>
