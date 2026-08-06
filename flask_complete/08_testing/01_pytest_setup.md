# 08-1 · pytest setup & fixtures

> **Level:** Intermediate · **Prerequisites:** [04-1 · The application factory](../04_app_structure/01_app_factory.md)
> **Time:** 50 min · **Verified:** 2026-07-29 (pytest 9.1.1 — FlaskNotes: 20 passed in ~3 s)

## Why this matters

This is where the application factory earns its keep. Because `create_app()` is a *function*, every test can build its own app with an in-memory database — fully isolated, no state leaking between tests, no running server. That's what makes a Flask suite fast and trustworthy.

---

## The `app` fixture

```python
# tests/conftest.py
import pytest
from app import create_app
from app.extensions import db as _db

@pytest.fixture
def app():
    app = create_app("testing")            # TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite://"
    with app.app_context():                # extensions need an app context
        _db.create_all()                   # fresh schema
        yield app                          # ← the test runs here
        _db.session.remove()
        _db.drop_all()                     # cleanup
```

Three things make this work:

- **`create_app("testing")`** selects `TestingConfig` — `sqlite://` is an **in-memory** database that exists only for this test.
- **`with app.app_context()`** — `db` needs to know which app it belongs to outside a request ([04-1](../04_app_structure/01_app_factory.md)).
- **`yield`** — everything after it is teardown, so each test starts clean.

---

## The `client` fixture

Flask ships a test client that calls your app **in-process** — no server, no network:

```python
@pytest.fixture
def client(app):
    return app.test_client()
```

```python
def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}
```

It mirrors a real HTTP client: `client.get/post/patch/delete(...)`, with `.status_code`, `.get_json()`, `.data`, `.headers`.

---

## Fixtures compose

Build higher-level fixtures on lower ones so tests stay short:

```python
@pytest.fixture
def user(app):
    u = User(email="ada@example.com")
    u.set_password("password123")
    _db.session.add(u); _db.session.commit()
    return u

@pytest.fixture
def auth_client(client, user):
    """A client with a logged-in session (web UI)."""
    client.post("/login", data={"email": "ada@example.com", "password": "password123"})
    return client                          # the session cookie is now stored in the client

@pytest.fixture
def token(client, user):
    r = client.post("/api/v1/auth/token",
                    json={"email": "ada@example.com", "password": "password123"})
    return r.get_json()["access_token"]

@pytest.fixture
def api_client(client, token):
    """A client that sends the bearer token on every request."""
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client
```

Now a test that needs a logged-in user just asks for `auth_client`; an API test asks for `api_client`. No auth boilerplate repeated 20 times.

> **Tip — the test client keeps cookies.** After `client.post("/login", ...)` the session cookie is retained for later requests on that client, which is exactly how a browser behaves. That's why `auth_client` is just "a client that logged in".

---

## Testing config

```python
class TestingConfig(Config):
    TESTING = True                          # propagates exceptions, disables error catching
    SQLALCHEMY_DATABASE_URI = "sqlite://"    # in-memory
    WTF_CSRF_ENABLED = False                 # forms don't need CSRF tokens in tests
```

`TESTING = True` makes Flask re-raise exceptions instead of returning a generic 500, so a bug shows you the traceback.

---

## Running it

```bash
pytest -q
```

**Output (real run — FlaskNotes):**
```
....................                                                     [100%]
20 passed in 2.98s
```

Twenty tests — web pages, auth, uploads, JSON API, ownership — in three seconds, with no database server and no running app.

---

## Recap & next

- ✅ `create_app("testing")` + `app_context()` + `create_all()/drop_all()` = a fresh app and DB per test.
- ✅ `app.test_client()` calls the app in-process; it mirrors an HTTP client and **keeps cookies**.
- ✅ Compose fixtures (`user` → `auth_client` / `token` → `api_client`) so tests stay short.
- ✅ `TESTING=True` re-raises exceptions; `sqlite://` is in-memory.
- ✅ Self-check: why can't you write this fixture if your app is created at module level?

→ Next: **[08-2 · Testing views, API & DB](02_testing_endpoints_db.md)**

## Exercises

1. Add an `admin_user` fixture (a second user) and use it to write a test that two users' data don't mix.

<details>
<summary>Solution</summary>

Create the second user in a fixture, get *their* token, and assert they can't see the first user's notes. FlaskNotes' `test_ownership_isolation` does exactly this — see [08-2](02_testing_endpoints_db.md).
</details>
