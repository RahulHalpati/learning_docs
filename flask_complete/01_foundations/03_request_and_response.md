# 01-3 · Request & response

> **Level:** Beginner · **Prerequisites:** [01-2 · Routing & URL variables](02_routing_and_variables.md)
> **Time:** 35 min · **Verified:** 2026-07-29 (Flask 3.1.3)

## Why this matters

A view function's job is: read the incoming **request**, do something, return a **response**. Flask exposes the request through a context-local object called `request` — one of the framework's defining ideas — and gives you several ways to shape what goes back.

---

## The `request` object

`request` is importable from `flask` and always refers to **the request currently being handled**:

```python
from flask import request

@app.get("/search")
def search():
    q = request.args.get("q", "")                    # query string ?q=
    page = request.args.get("page", 1, type=int)     # with default AND conversion
    return {"q": q, "page": page, "method": request.method, "path": request.path}
```

**Output (real run):**
```
GET /search?q=flask&page=3  ->  {'q': 'flask', 'page': 3, 'method': 'GET', 'path': '/search'}
GET /search                 ->  {'q': '',      'page': 1, 'method': 'GET', 'path': '/search'}
```

`args.get(key, default, type=int)` is the workhorse: it defaults *and* converts, so `page` is a real `int` and a missing/garbage value can't crash the view.

### What's on `request`

| Attribute | Contains |
|-----------|----------|
| `request.args` | query string params (`?q=…`) |
| `request.form` | form fields (POSTed HTML form) |
| `request.files` | uploaded files |
| `request.get_json()` | parsed JSON body |
| `request.headers` | request headers |
| `request.cookies` | cookies |
| `request.method`, `.path`, `.url` | request metadata |

```python
@app.post("/echo")
def echo():
    return jsonify(received=request.get_json(silent=True),
                   content_type=request.content_type)
```

**Output (real run, POSTing `{"a": 1}`):**
```
{'received': {'a': 1}, 'content_type': 'application/json'}
```

> **Tip — `get_json(silent=True)`.** Plain `get_json()` raises a 415/400 if the body isn't valid JSON. `silent=True` returns `None` instead, letting you produce your own error message. Pattern: `data = request.get_json(silent=True) or {}`.

Headers are case-insensitive:

**Output (real run, with `User-Agent: demo/1.0`):**
```
{'ua': 'demo/1.0'}
```

---

## How `request` can be a global

`request` is a **context local** — it looks like a module-level global but Flask swaps in the right object per request (and per thread/task). That's why you never pass a request object around in Flask, unlike most frameworks. Its siblings:

| Object | Is |
|--------|-----|
| `request` | the current request |
| `session` | the signed cookie session ([06-1](../06_auth_and_sessions/01_sessions_cookies.md)) |
| `g` | a scratchpad for **this request** (e.g. the current user) |
| `current_app` | the active application ([04-1](../04_app_structure/01_app_factory.md)) |

Touch them outside a request and you get *"Working outside of request context"* — the classic Flask error. That's what `app.test_request_context()` is for in scripts and tests.

---

## Shaping the response

Returning a value is usually enough, but for full control use `make_response`:

```python
from flask import make_response

@app.get("/custom")
def custom():
    resp = make_response({"ok": True}, 201)
    resp.headers["X-Demo"] = "yes"
    resp.set_cookie("seen", "1")
    return resp
```

**Output (real run):**
```
201  |  X-Demo: yes  |  {'ok': True}
```

Use `make_response` when you need to set headers or cookies; use the plain return value or a `(body, status)` tuple for everything else.

`jsonify(...)` is the explicit JSON helper (it accepts keyword args and handles more types than the bare-dict shortcut) — useful when you want to be unambiguous.

---

## Recap & next

- ✅ `request` is a **context local** giving you `args`, `form`, `files`, `get_json()`, `headers`, `cookies`.
- ✅ `args.get(key, default, type=int)` defaults *and* converts in one call.
- ✅ `get_json(silent=True) or {}` avoids a hard failure on a bad body.
- ✅ Siblings: `session`, `g` (per-request scratchpad), `current_app`; outside a request they raise.
- ✅ `make_response(...)` when you need headers/cookies; tuples otherwise.
- ✅ Self-check: what does *"Working outside of request context"* mean, and when would you hit it?

→ Next: **[02 · Templates & static](../02_templates_and_static/README.md)**

## Exercises

1. Write `GET /debug` returning the method, path, all query args as a dict, and the `User-Agent` header.

<details>
<summary>Solution</summary>

```python
@app.get("/debug")
def debug():
    return {
        "method": request.method,
        "path": request.path,
        "args": request.args.to_dict(),          # MultiDict -> plain dict
        "user_agent": request.headers.get("User-Agent"),
    }
```
`request.args` is a `MultiDict` (a key can repeat); `.to_dict()` flattens it for JSON.
</details>
