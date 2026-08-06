# 01-2 · Routing & URL variables

> **Level:** Beginner · **Prerequisites:** [01-1 · Your first app](01_first_app.md)
> **Time:** 35 min · **Verified:** 2026-07-29 (Flask 3.1.3)

## Why this matters

URLs carry data — `/posts/42`, `/users/ada`. Flask captures those parts as function arguments and can **convert and validate** them for you. Plus `url_for()` builds URLs from route *names*, so changing a path doesn't break every link in your app.

---

## Variable rules

Put `<name>` in the path and take a matching argument:

```python
@app.get("/users/<username>")
def show_user(username):
    return f"User: {username}"

@app.get("/posts/<int:post_id>")            # converter: must be an integer
def show_post(post_id):
    return {"post_id": post_id, "type": type(post_id).__name__}
```

**Output (real run):**
```
GET /users/ada    ->  User: ada
GET /posts/42     ->  {'post_id': 42, 'type': 'int'}
```

Note `'type': 'int'` — the `int:` converter **converted** it, so you get a real integer, not `"42"`. A non-integer (`/posts/abc`) simply doesn't match the route → **404**.

### The converters

| Converter | Matches | Example |
|-----------|---------|---------|
| *(default)* `string` | any text without `/` | `<username>` |
| `int` | integers (converted) | `<int:post_id>` |
| `float` | decimals | `<float:price>` |
| `path` | text **including** `/` | `<path:subpath>` |
| `uuid` | a UUID | `<uuid:id>` |

`path` is the one worth remembering — it's how you capture a nested file path:

**Output (real run):**
```
GET /path/a/b/c.txt   ->  {'subpath': 'a/b/c.txt'}
```

---

## HTTP methods

```python
@app.get("/notes")          # read
@app.post("/notes")         # create
@app.route("/notes/<int:i>", methods=["GET", "PATCH", "DELETE"])   # several at once
```

Call a route with a method it doesn't allow and Flask returns **405 Method Not Allowed** automatically:

**Output (real run, POST to a GET-only route):**
```
405
```

---

## `url_for` — never hard-code a URL

Build URLs from the **view function's name**, not a string:

```python
url_for("show_post", post_id=7)     # -> /posts/7
url_for("search", q="x")            # -> /search?x  (extra kwargs become query args)
```

**Output (real run):**
```
/posts/7  |  /search?q=x
```

Two things happen here: path variables get filled in, and **any leftover keyword becomes a query parameter**. Use `url_for` in templates and redirects always — then changing `@app.get("/posts/<int:post_id>")` to `/articles/<int:post_id>` updates every link in the app automatically.

> **Tip — endpoint names.** The first argument is the *endpoint*, which defaults to the function's name. Inside a blueprint it's prefixed: `url_for("web.index")`, `url_for("auth.login")` ([04-2](../04_app_structure/02_blueprints.md)). Getting `BuildError: Could not build url for endpoint 'x'` almost always means a missing (or wrong) blueprint prefix.

---

## Redirects and aborting

```python
from flask import redirect, url_for, abort

@app.get("/old")
def old():
    return redirect(url_for("index"))        # 302 by default

@app.get("/boom")
def boom():
    abort(403)                               # raise an HTTP error immediately
```

**Output (real run):**
```
GET /old   ->  302, Location: /
GET /boom  ->  403
```

`abort(404)` / `abort(403)` is the idiomatic way to bail out of a view with an error status — Flask raises the matching exception, which your error handlers can format ([07-1](../07_errors_logging_cors/01_error_handling.md)).

---

## Recap & next

- ✅ `<var>` captures URL parts; converters (`int`, `float`, `path`, `uuid`) convert **and** validate — a mismatch is a 404.
- ✅ `@app.get/post/...` or `methods=[...]`; a wrong method yields **405** automatically.
- ✅ **`url_for("endpoint", **values)`** builds URLs — never hard-code paths; extra kwargs become query args.
- ✅ `redirect(url_for(...))` and `abort(code)` for flow control.
- ✅ Self-check: why does `/posts/abc` return 404 rather than 400 on a route declared `<int:post_id>`?

→ Next: **[01-3 · Request & response](03_request_and_response.md)**

## Exercises

1. Add `GET /files/<path:filepath>` that echoes the captured path, and confirm it captures `docs/2026/report.pdf` in one variable.

<details>
<summary>Solution</summary>

```python
@app.get("/files/<path:filepath>")
def files(filepath):
    return {"filepath": filepath, "depth": filepath.count("/") + 1}
```
Only the `path` converter allows `/` inside the value — with the default `string` converter the route wouldn't match at all.
</details>
