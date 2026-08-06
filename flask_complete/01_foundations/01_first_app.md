# 01-1 · Your first app

> **Level:** Beginner · **Prerequisites:** [00 · Introduction](../00_introduction.md)
> **Time:** 30 min · **Verified:** 2026-07-29 (Flask 3.1.3)

## Why this matters

Flask's whole model fits in five lines. Get those five lines and running/reloading working, and every later lesson is "add another route".

---

## The app

```python
# app.py
from flask import Flask

app = Flask(__name__)          # __name__ tells Flask where to find templates/static

@app.get("/")                  # register this function for GET /
def index():
    return "Hello, Flask!"
```

- **`Flask(__name__)`** — the application object. `__name__` lets Flask locate your package's `templates/` and `static/` folders.
- **`@app.get("/")`** — a decorator that binds a URL to a function. (`@app.route("/")` is the classic form; `@app.get/post/put/patch/delete` are the modern shortcuts.)
- **The return value** becomes the response body.

**Output (real run):**
```
Hello, Flask!
```

---

## Running it

```bash
flask --app app run --debug
```

**Output (real run):**
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

- **`--app app`** — the module (`app.py`) holding your `app` object. Flask also auto-detects `app.py` / `wsgi.py`.
- **`--debug`** — **auto-reload** on save and a browser traceback when something breaks.

> ⚠️ **Never run with `--debug` in production.** The debugger exposes an interactive console — anyone who triggers an error could run arbitrary code on your server. It's a development-only convenience, and `flask run` itself is a development-only server ([09](../09_production/README.md)).

---

## What you can return

Flask is flexible about return values:

```python
@app.get("/text")
def text():   return "plain string"                  # → 200, text/html

@app.get("/json")
def json():   return {"framework": "flask"}          # → dict becomes JSON automatically

@app.get("/created")
def created(): return {"ok": True}, 201              # → (body, status)

@app.get("/with-headers")
def hdr():    return {"ok": True}, 200, {"X-Demo": "yes"}   # → (body, status, headers)
```

Returning a **dict** (or list) auto-serializes to JSON — no `jsonify` needed for the simple case. The tuple forms let you set a status code and headers inline.

---

## The two ways to run

| Command | For |
|---------|-----|
| `flask --app app run --debug` | development — reload, debugger |
| `gunicorn 'wsgi:app'` | production ([09-1](../09_production/01_gunicorn_wsgi.md)) |

You'll use the first all course, and switch to the second at the end.

---

## Recap & next

- ✅ `app = Flask(__name__)` + a decorated function = a complete Flask app.
- ✅ `@app.get(...)` (or `@app.route(...)`) binds a URL to a view function.
- ✅ Return a string, a **dict** (auto-JSON), or a `(body, status, headers)` tuple.
- ✅ `flask --app app run --debug` for dev; **never** debug mode in production.
- ✅ Self-check: why does `Flask(__name__)` need `__name__` at all?

→ Next: **[01-2 · Routing & URL variables](02_routing_and_variables.md)**

## Exercises

1. Add `GET /about` returning a dict with your app's name and version, and confirm the JSON in the browser.

<details>
<summary>Solution</summary>

```python
@app.get("/about")
def about():
    return {"app": "FlaskNotes", "version": "1.0.0"}
```
The dict is serialized to JSON with `Content-Type: application/json` automatically — Flask 2.2+ behavior, no `jsonify` required.
</details>
