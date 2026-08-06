# 07-1 · Error handling

> **Level:** Intermediate · **Prerequisites:** [04-2 · Blueprints](../04_app_structure/02_blueprints.md)
> **Time:** 45 min · **Verified:** 2026-07-29 (Flask 3.1.3)

## Why this matters

FlaskNotes serves **both** HTML pages and a JSON API, so a 404 must be a friendly page for a browser and a JSON object for an API client. And an unexpected crash must never show a user your stack trace. Central error handlers solve both — in about 20 lines.

---

## A domain exception

Let API code raise something meaningful instead of building responses inline:

```python
class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status
```

```python
raise ApiError("Note not found", 404)          # in a view or helper
```

---

## The three handlers

```python
from werkzeug.exceptions import HTTPException

def _wants_json() -> bool:
    return request.path.startswith("/api/")      # content negotiation by path

def register_error_handlers(app):
    @app.errorhandler(ApiError)                          # 1. your own errors
    def handle_api_error(exc):
        return jsonify(error={"message": exc.message, "status": exc.status}), exc.status

    @app.errorhandler(HTTPException)                     # 2. 404/403/405/413... from Flask
    def handle_http_exception(exc):
        if _wants_json():
            return jsonify(error={"message": exc.description, "status": exc.code}), exc.code
        if exc.code == 404:
            return render_template("404.html"), 404
        return render_template("error.html", error=exc), exc.code

    @app.errorhandler(Exception)                         # 3. anything unexpected -> 500
    def handle_unexpected(exc):
        logger.exception("Unhandled exception: %s", exc)      # full detail for US
        if _wants_json():
            return jsonify(error={"message": "Internal server error", "status": 500}), 500
        return render_template("error.html", error=None), 500
```

Registered in the factory with `register_error_handlers(app)`.

**Output (real run):**
```
GET /api/missing   ->  404  {'error': {'message': 'Note not found', 'status': 404}}
GET /api/nope      ->  404  {'error': {'message': 'The requested URL was not found...', 'status': 404}}
GET /nope          ->  404  <h1>404</h1>            (HTML — is_json: False)
GET /api/crash     ->  500  {'error': {'message': 'Internal server error', 'status': 500}}
```

Same app, same 404, two representations — decided by the path. And the crash returned a generic message while the real `ValueError: kaboom` traceback went to the log.

> ⚠️ **Never send exception text to the client on a 500.** `str(exc)` can contain a SQL query, a file path, or a secret. Log the detail privately (`logger.exception` captures the traceback), return something generic publicly. The `ApiError` messages are safe because *you* wrote them deliberately.

---

## Why catch `HTTPException` separately

Werkzeug raises `HTTPException` subclasses for `abort(404)`, unmatched routes, 405s, and `413` from `MAX_CONTENT_LENGTH`. Catching the base class handles them all — and it must come *before* the generic `Exception` handler in your thinking, since Flask picks the most specific registered handler.

---

## Handling errors in the web UI

For form pages, a flash + re-render is friendlier than an error page:

```python
if not title:
    flash("Title is required.", "error")
    return render_template("new_note.html"), 400      # keep the 400 status, show the form
```

FlaskNotes does this for validation and reserves the error *pages* for 404/500.

---

## Recap & next

- ✅ One `ApiError` + three handlers (`ApiError`, `HTTPException`, `Exception`) covers everything.
- ✅ **Content negotiation**: JSON for `/api/*`, rendered pages elsewhere — one app, two audiences.
- ✅ Log the real exception; return a **generic** 500 message. Never leak internals.
- ✅ In forms, flash + re-render with the right status beats a full error page.
- ✅ Self-check: why does the 500 handler log `exc` but not include it in the response?

→ Next: **[07-2 · Logging](02_logging.md)**

## Exercises

1. Add a `413` case: upload something over `MAX_CONTENT_LENGTH` and make the handler return a friendly "File too large (max 2 MB)" — JSON for the API, flash for the form.

<details>
<summary>Solution</summary>

`RequestEntityTooLarge` is an `HTTPException`, so it already routes through handler #2 — just special-case `exc.code == 413` to swap in a clearer message. No new handler needed, which is the benefit of catching the base class.
</details>
