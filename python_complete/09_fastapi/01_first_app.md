# 01 · First App

> **Level:** Advanced · **Prerequisites:** [Section 08](../08_async/README.md)
> **Time:** ~1 hour · **Verified:** 2026-06-04 (FastAPI 0.136.3)

## Why this matters

Every web service starts with one route returning one response. This module gets a FastAPI app running, explains the HTTP basics you need, shows the auto-generated interactive docs (FastAPI's superpower), and verifies it all with `TestClient`. From here, every feature is an addition to this skeleton.

## Concept: a minimal HTTP refresher

An API speaks **HTTP**. The two pieces you need now:

- **Method + path** describe *what* the client wants: `GET /items` ("read items"), `POST /items` ("create an item"). Common methods: `GET` (read), `POST` (create), `PUT`/`PATCH` (update), `DELETE` (remove).
- **Status code** describes *how it went*: `200` OK, `201` Created, `404` Not Found, `422` Unprocessable (validation failed), `500` Server Error.

FastAPI maps each method+path to a Python function. The function's return value becomes the JSON response.

## Concept: your first app

```python
# main.py
from fastapi import FastAPI

app = FastAPI()                      # the application object

@app.get("/")                        # register a GET handler for the path "/"
def root():
    return {"message": "Hello, FastAPI!"}   # a dict becomes JSON automatically
```

Three things:
1. `app = FastAPI()` creates the application.
2. `@app.get("/")` is a **decorator** ([Section 06.03](../06_pythonic_intermediate/03_decorators.md)) registering `root` to handle `GET /`. (Remember decorators-with-arguments? `@app.get("/")` is exactly that pattern.)
3. Returning a dict → FastAPI serialises it to JSON and sends it with status `200`.

## Concept: running it with uvicorn

FastAPI apps run on an **ASGI server** — `uvicorn` is the standard one. ASGI (Asynchronous Server Gateway Interface) is the async successor to the old WSGI standard; it's what lets FastAPI handle async endpoints.

```bash
uvicorn main:app --reload
```

- `main:app` means "the `app` object in `main.py`".
- `--reload` restarts the server when you edit code (development only).

You'll see:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Now visit <http://127.0.0.1:8000/> in a browser and you'll get `{"message":"Hello, FastAPI!"}`.

## Concept: verifying with `TestClient` (what this course does)

Rather than start a server, we test the app *in-process* with `TestClient` — it sends real requests to your app object and returns real responses. This is also how you'll write automated tests ([Module 07](07_testing.md)).

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello, FastAPI!"}

client = TestClient(app)
response = client.get("/")
print(response.status_code)      # 200
print(response.json())           # {'message': 'Hello, FastAPI!'}
```

Output (verified):

```text
200
{'message': 'Hello, FastAPI!'}
```

`TestClient(app)` wraps your app; `client.get("/")` returns a response object with `.status_code` and `.json()`. No network, no separate process — perfect for learning and testing.

> ℹ️ On this course's exact versions you may see a `StarletteDeprecationWarning` about `httpx`/`httpx2` when constructing `TestClient`. It's harmless (a packaging detail in this specific combination) and doesn't affect behaviour.

## Concept: multiple routes

Add as many routes as you like — each method+path pair gets its own function:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
def root():
    return {"service": "demo", "status": "ok"}

@app.get("/health")
def health():
    return {"healthy": True}

@app.get("/version")
def version():
    return {"version": "1.0.0"}

client = TestClient(app)
print(client.get("/").json())
print(client.get("/health").json())
print(client.get("/version").json())
```

Output (verified):

```text
{'service': 'demo', 'status': 'ok'}
{'healthy': True}
{'version': '1.0.0'}
```

```mermaid
flowchart LR
    C["Client"] -->|"GET /health"| A["FastAPI app"]
    A -->|"routes to"| H["health() function"]
    H -->|"return dict"| A
    A -->|"JSON 200"| C
```

## Concept: the automatic interactive docs ⭐

This is FastAPI's standout feature. From your code alone, it generates **interactive API documentation** — no extra work. When the server is running, open:

- **<http://127.0.0.1:8000/docs>** — Swagger UI: a live page listing every route, with "Try it out" buttons to send real requests from the browser.
- **<http://127.0.0.1:8000/redoc>** — ReDoc: a clean, readable reference version.

The docs are built from your routes, type hints, and Pydantic models (next modules). As you add validated parameters and request bodies, the docs automatically show their types, constraints, and examples. This means your API is *always* documented and explorable — a huge productivity and collaboration win.

> 🧠 The docs come from an **OpenAPI** schema FastAPI generates (available at `/openapi.json`). OpenAPI is an industry standard, so your API can also auto-generate client libraries, Postman collections, and more.

## Concept: sync vs async route functions

A route function can be `def` (regular) **or** `async def` (coroutine — [Section 08](../08_async/README.md)). FastAPI handles both:

```python
@app.get("/sync")
def sync_route():
    return {"type": "sync"}

@app.get("/async")
async def async_route():
    return {"type": "async"}        # use async when you AWAIT things (DB, HTTP)
```

- Use **`async def`** when the handler `await`s async operations (async database, async HTTP calls) — this is where FastAPI's concurrency shines.
- Use plain **`def`** for simple/CPU or when calling *blocking* libraries — FastAPI runs these in a threadpool so they don't block the event loop (it handles the [pitfall from Section 08.04](../08_async/04_async_pitfalls.md) for you).

Both return the same way. We'll use `async def` in later modules to model real I/O.

## Common mistakes

**Mistake: wrong `uvicorn` target**
```bash
uvicorn app:main --reload      # backwards!
```
```text
ERROR: Error loading ASGI app. Could not import module "app".
```
**Why:** the format is `filename:app_variable`. If your file is `main.py` and the FastAPI object is `app`, it's `uvicorn main:app`.

**Mistake: returning something non-serialisable**
```python
@app.get("/bad")
def bad():
    return {1, 2, 3}        # a set isn't JSON-serialisable
```
**Why:** the response must be convertible to JSON (dicts, lists, strings, numbers, booleans, `None`, Pydantic models). A raw `set` fails. Return a list instead. (Pydantic models, Module 03, handle complex types cleanly.)

## Practice

**Exercise:** Build an app with three routes: `GET /` returning `{"app": "todo-api"}`, `GET /ping` returning `{"pong": True}`, and `GET /info` returning a dict with `name` and `version`. Verify all three with `TestClient`.

<details><summary>Solution</summary>

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/")
def root():
    return {"app": "todo-api"}

@app.get("/ping")
def ping():
    return {"pong": True}

@app.get("/info")
def info():
    return {"name": "todo-api", "version": "0.1.0"}

client = TestClient(app)
print(client.get("/").json())
print(client.get("/ping").json())
print(client.get("/info").json())
```

Output:

```text
{'app': 'todo-api'}
{'pong': True}
{'name': 'todo-api', 'version': '0.1.0'}
```

Each `@app.get(path)` registers a handler; returning a dict produces a JSON `200` response, confirmed via `TestClient`.
</details>

## Recap & next

- ✅ Created a FastAPI app and registered routes with `@app.get(...)`.
- ✅ Returned dicts that become JSON; understood HTTP methods and status codes.
- ✅ Ran it with `uvicorn main:app --reload` and verified with `TestClient`.
- ✅ Discovered the **automatic interactive docs** at `/docs` and `/redoc`.
- ✅ Learned sync `def` vs `async def` route functions.
- Self-check: what does `uvicorn main:app` mean, piece by piece?

→ Next: **[02 · Parameters & validation](02_parameters_and_validation.md)**
