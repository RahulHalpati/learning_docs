# 08-2 · Testing views, API & DB

> **Level:** Intermediate · **Prerequisites:** [08-1 · pytest setup & fixtures](01_pytest_setup.md)
> **Time:** 50 min · **Verified:** 2026-07-29 (pytest 9.1.1 — 20 passed)

## Why this matters

With fixtures in place, tests read like a specification. The value isn't in testing the happy path — that usually works — it's in pinning down **auth**, **validation**, **error paths**, and **isolation between users**, which are what silently break.

---

## Testing HTML pages

Assert on status codes and page content:

```python
def test_index_renders_for_anonymous(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Please" in r.data                    # the "log in" prompt

def test_new_note_requires_login(client):
    r = client.get("/notes/new")
    assert r.status_code == 302                    # redirected...
    assert "/login" in r.headers["Location"]       # ...to the login page
```

`r.data` is bytes, so compare against `b"..."`. Use `follow_redirects=True` when you want the final page instead of the 302.

---

## Testing the auth flow

```python
def test_register_then_see_empty_notes(client):
    r = client.post("/register", data={"email": "new@example.com",
                                       "password": "password123"},
                    follow_redirects=True)
    assert b"No notes yet" in r.data

def test_login_wrong_password_is_401(client, user):
    r = client.post("/login", data={"email": "ada@example.com", "password": "nope"})
    assert r.status_code == 401
    assert b"Incorrect email or password" in r.data
```

Form posts use `data=` (form-encoded); JSON endpoints use `json=`.

---

## Testing file uploads

Pass a `(file-like, filename)` tuple with `content_type="multipart/form-data"`:

```python
import io

def test_create_note_with_image_upload(auth_client):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    r = auth_client.post("/notes/new", data={
        "title": "With picture",
        "image": (io.BytesIO(png), "photo.png"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert r.status_code == 200
    assert b"<img" in r.data                       # the template rendered it

def test_rejects_disallowed_file_type(auth_client):
    r = auth_client.post("/notes/new", data={
        "title": "Bad file",
        "image": (io.BytesIO(b"hi"), "notes.txt"),
    }, content_type="multipart/form-data")
    assert r.status_code == 415
```

You never touch the filesystem in the test — `io.BytesIO` is enough.

---

## Testing the JSON API

```python
def test_create_and_get_note(api_client):
    r = api_client.post("/api/v1/notes", json={"title": "Shopping", "body": "milk"})
    assert r.status_code == 201
    note = r.get_json()
    assert api_client.get(f"/api/v1/notes/{note['id']}").get_json()["body"] == "milk"

def test_notes_require_a_token(client):
    assert client.get("/api/v1/notes").status_code == 401
```

Cover validation with `parametrize` — one body, many cases:

```python
@pytest.mark.parametrize("payload,expected", [
    ({"title": ""}, 422),
    ({}, 422),
    ({"title": "Valid"}, 201),
])
def test_create_validation(api_client, payload, expected):
    assert api_client.post("/api/v1/notes", json=payload).status_code == expected
```

Each case reports separately, so a failure tells you exactly which input broke.

---

## The most important test: isolation

```python
def test_ownership_isolation(client, api_client):
    nid = api_client.post("/api/v1/notes", json={"title": "Secret"}).get_json()["id"]

    other = User(email="bob@example.com"); other.set_password("password123")
    db.session.add(other); db.session.commit()
    tok = client.post("/api/v1/auth/token",
                      json={"email": "bob@example.com", "password": "password123"}
                      ).get_json()["access_token"]

    r = client.get(f"/api/v1/notes/{nid}", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403                              # authenticated, not entitled
    assert client.get("/api/v1/notes",
                      headers={"Authorization": f"Bearer {tok}"}).get_json()["total"] == 0
```

If ownership logic ever regresses, this goes red before a user's private notes leak. Every multi-user app needs this test.

---

## What to cover (priority order)

1. **Auth** — protected routes reject anonymous callers (401/302).
2. **Isolation** — user A can't read/modify user B's data (403, empty lists).
3. **Validation** — bad input → 422/400, not a 500.
4. **Error paths** — 404 for missing, 415/413 for uploads.
5. **Happy paths** — the CRUD flows.

> **Tip — test behavior, not implementation.** Assert on responses (status, JSON, rendered HTML), not on which internal function ran. Then you can refactor — move a route into a blueprint, swap the ORM query — and green tests prove the contract still holds. That's how a suite stays an asset instead of becoming a maintenance burden.

---

## Recap & next

- ✅ Pages: assert status + `b"bytes"` in `r.data`; `follow_redirects=True` for the final page.
- ✅ Forms use `data=`, APIs use `json=`, uploads use a `(BytesIO, filename)` tuple + multipart.
- ✅ `@pytest.mark.parametrize` covers validation matrices compactly.
- ✅ **Test ownership isolation** — the one that prevents a data leak.
- ✅ Priorities: auth → isolation → validation → errors → happy path.
- ✅ Self-check: which single test would catch a regression letting one user read another's notes?

→ Next: **[09 · Production](../09_production/README.md)**

## Exercises

1. Write a test that a note created via the **API** shows up on the **web** page for the same user (both faces, one database).

<details>
<summary>Solution</summary>

Use both fixtures on the same user: `api_client.post("/api/v1/notes", json={"title": "X"})`, then `auth_client.get("/")` and assert `b"X" in r.data`. It proves the web and API blueprints really do share one data layer — a nice integration check.
</details>
