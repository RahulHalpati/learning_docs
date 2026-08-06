# 04-2 · Blueprints

> **Level:** Intermediate · **Prerequisites:** [04-1 · The application factory](01_app_factory.md)
> **Time:** 45 min · **Verified:** 2026-07-29 (Flask 3.1.3)

## Why this matters

A **blueprint** is a group of routes (plus its own templates, static files, and error handlers) that you register onto an app. It's Flask's answer to "my app has 40 routes in one file" — and it's what lets several people work on different features without constant merge conflicts.

---

## Define and register

```python
# app/blueprints/api.py
from flask import Blueprint

api_bp = Blueprint("api", __name__)          # "api" is the blueprint's NAME

@api_bp.get("/notes")
def list_notes():
    return {"items": []}
```

```python
# app/__init__.py — inside create_app()
from app.blueprints.api import api_bp
app.register_blueprint(api_bp, url_prefix="/api/v1")
```

The route above now lives at **`/api/v1/notes`**. The prefix is applied at registration, so the same blueprint could be mounted at `/api/v2` later without editing any route.

**Output (real run):**
```
GET /notes/  ->  {'bp': 'notes', 'app': ...}      (blueprint handling the request)
```

---

## Endpoint names get namespaced

This is the part that trips everyone up. Inside a blueprint, `url_for` needs the **blueprint name** as a prefix:

```python
url_for("index")            # ❌ BuildError — no such endpoint
url_for("web.index")        # ✅ blueprint "web", view "index"
url_for("auth.login")       # ✅
```

> ⚠️ **This is the #1 blueprint error.** `BuildError: Could not build url for endpoint 'login'. Did you mean 'auth.login'?` means you forgot the prefix. It bites in templates (`{{ url_for('web.index') }}`) and in extension config — FlaskNotes sets `login_manager.login_view = "auth.login"`, and using `"login"` there breaks every `@login_required` redirect. (That exact bug appeared while building this course; the test suite caught it.)
>
> Inside the *same* blueprint you can use a relative `.` shortcut: `url_for(".index")`.

---

## Three blueprints, three concerns

FlaskNotes splits by feature — the standard approach:

| Blueprint | Prefix | Owns |
|-----------|--------|------|
| `web` | `/` | HTML pages, Jinja templates, uploads |
| `auth` | `/` | register / login / logout (session) |
| `api` | `/api/v1` | JSON endpoints, JWT auth |

```python
app.register_blueprint(web_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp, url_prefix="/api/v1")
```

The payoff is visible in the error handling ([07-1](../07_errors_logging_cors/01_error_handling.md)): because API routes share a `/api/` prefix, one handler can return **JSON** for them and **HTML** pages for everything else.

---

## Blueprint-local extras

A blueprint can carry more than routes:

```python
bp = Blueprint("admin", __name__,
               url_prefix="/admin",
               template_folder="templates",     # its own templates
               static_folder="static")

@bp.before_request                              # runs before every route in THIS blueprint
def require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)

@bp.errorhandler(404)                           # blueprint-scoped error handler
def not_found(e):
    return render_template("admin/404.html"), 404
```

`@bp.before_request` is the idiomatic way to protect an entire section — one guard instead of a decorator on twenty views.

---

## Recap & next

- ✅ A **blueprint** groups routes (+ templates/static/handlers); register it with an optional `url_prefix`.
- ✅ Endpoints are namespaced: **`url_for("blueprint.view")`** — forgetting the prefix is the classic `BuildError`.
- ✅ Split by **feature** (`web`, `auth`, `api`), and mount APIs under a versioned prefix.
- ✅ `@bp.before_request` guards a whole section; blueprints can own templates and error handlers.
- ✅ Self-check: your template raises `BuildError: Could not build url for endpoint 'login'` — what's the fix?

→ Next: **[04-3 · Config & environments](03_config_and_env.md)**

## Exercises

1. Add an `admin` blueprint at `/admin` with a `@bp.before_request` that 403s non-admins, and one route inside it.

<details>
<summary>Solution</summary>

Create the blueprint with `url_prefix="/admin"`, add the `before_request` guard shown above, register it in `create_app()`. Every current *and future* route in that blueprint is protected automatically — which is why section-level guards beat per-view decorators.
</details>
