# 04-1 · The application factory

> **Level:** Intermediate · **Prerequisites:** [01-1 · Your first app](../01_foundations/01_first_app.md)
> **Time:** 45 min · **Verified:** 2026-07-29 (Flask 3.1.3, Flask-SQLAlchemy 3.1.1)

## Why this matters

A module-level `app = Flask(__name__)` works until you need a *second* configuration — which happens the moment you write tests. The **application factory** makes app creation a function, so you can build a dev app, a test app with an in-memory database, and a production app from the same code. It's the single most important Flask convention, and every modern extension is designed around it.

---

## The pattern

```python
# app/__init__.py
from flask import Flask
from app.config import config_by_name
from app.extensions import db, login_manager, migrate

def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name or "development"]())
    app.config.from_prefixed_env()          # FLASK_* env vars override

    db.init_app(app)                        # bind extensions to THIS app
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.blueprints.api import api_bp   # imported here to avoid circular imports
    from app.blueprints.web import web_bp
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    return app
```

Everything the app needs is assembled in one readable function: config → extensions → blueprints.

---

## The `init_app()` pattern

The trick that makes factories work: extensions are created **bare** in a separate module, then **bound** to an app inside the factory.

```python
# app/extensions.py — no app here!
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy(model_class=Base)
migrate = Migrate()
```

Why the split: `app/models.py` needs to `from app.extensions import db` at import time, but `db` must not be tied to any one app yet. `db.init_app(app)` does the binding later — so **one `db` object can serve many app instances**. Every well-maintained Flask extension supports this; it's a good sign of a modern one.

> ⚠️ **Never create the app at import time in a factory project.** `app = create_app()` at module level in `app/__init__.py` re-introduces exactly the problem the factory solves. Build it in `wsgi.py` (for gunicorn) and in your test fixtures — nowhere else.

---

## Why it pays off: tests

```python
@pytest.fixture
def app():
    app = create_app("testing")        # in-memory DB, TESTING=True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
```

Each test gets a **fresh, isolated app and database**. Without a factory you'd be monkey-patching a global app and fighting state leaks between tests. This fixture is the whole reason FlaskNotes' 20 tests are fast and independent ([08-1](../08_testing/01_pytest_setup.md)).

---

## The application context

Extensions like `db` need to know *which* app they're working with. Inside a request Flask sets that up automatically; outside one (a script, a fixture, a CLI command) you do it yourself:

```python
with app.app_context():
    db.create_all()                     # now `db` knows which app/config to use
```

Forget it and you get the classic error:

> `RuntimeError: Working outside of application context.`

Two context-local objects come with it:

| Object | Is | Lives for |
|--------|-----|-----------|
| **`current_app`** | the active app | the app context |
| **`g`** | a scratchpad (e.g. `g.current_user`) | **one request** |

`current_app` is how blueprint code reads config without importing the app (which would be circular): `current_app.config["UPLOAD_FOLDER"]`. FlaskNotes' API decorator stores the authenticated user on `g` so the view can read it — request-scoped, no globals.

---

## The layout this enables

```
app/
├── __init__.py        # create_app()
├── config.py          # config classes
├── extensions.py      # bare db, migrate, login_manager
├── models.py          # imports db from extensions
├── errors.py          # error handlers
└── blueprints/        # web.py, auth.py, api.py
wsgi.py                # app = create_app()   <- gunicorn's entrypoint
```

---

## Recap & next

- ✅ `create_app()` builds a configured app **on demand** — dev, testing, production from one codebase.
- ✅ Extensions are created bare in `extensions.py` and bound with **`init_app(app)`** — that split avoids circular imports.
- ✅ Outside a request, wrap work in **`with app.app_context()`**; use `current_app` for config and `g` for per-request data.
- ✅ Build the app only in `wsgi.py` and test fixtures — never at import time.
- ✅ Self-check: why can't `extensions.py` just do `db = SQLAlchemy(app)`?

→ Next: **[04-2 · Blueprints](02_blueprints.md)**

## Exercises

1. Convert a single-file app into a factory: move config to a class, extensions to `extensions.py`, and create the app in `wsgi.py`. Confirm `flask --app wsgi run` still works.

<details>
<summary>Solution</summary>

That's precisely FlaskNotes' layout. The check that it's right: you can call `create_app("testing")` and `create_app("development")` in the same process and they don't interfere — which is what the test fixture does.
</details>
