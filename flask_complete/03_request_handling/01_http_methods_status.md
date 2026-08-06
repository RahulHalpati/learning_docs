# 03-1 · HTTP methods & status codes

> **Level:** Beginner · **Prerequisites:** [01-2 · Routing & URL variables](../01_foundations/02_routing_and_variables.md)
> **Time:** 30 min · **Verified:** 2026-07-29 (Flask 3.1.3)

## Why this matters

Methods and status codes are the vocabulary of HTTP. Getting them right isn't pedantry — browsers, caches, proxies, and client libraries *act* on them. A write behind a GET will eventually be triggered by a crawler; a 200 where you meant 404 breaks every client's error handling.

---

## The methods

| Method | Means | Body? | Typical success |
|--------|-------|:-----:|-----------------|
| **GET** | read | no | `200 OK` |
| **POST** | create / trigger an action | yes | `201 Created` |
| **PUT** | replace entirely | yes | `200 OK` |
| **PATCH** | update part | yes | `200 OK` |
| **DELETE** | remove | no | `204 No Content` |

```python
@app.get("/notes")                    # list
@app.post("/notes")                   # create -> 201
@app.get("/notes/<int:i>")            # read one
@app.patch("/notes/<int:i>")          # partial update
@app.delete("/notes/<int:i>")         # delete -> 204
```

The same path serves several methods; the method is part of the route's identity. Call an unsupported one and Flask returns **405** automatically.

---

## Safe & idempotent

**Safe** = changes nothing. **Idempotent** = doing it twice equals doing it once.

| Method | Safe | Idempotent | Consequence |
|--------|:----:|:----------:|-------------|
| GET | ✅ | ✅ | cacheable, prefetchable, freely retried |
| POST | ❌ | ❌ | a double-submit creates **two** records |
| PUT | ❌ | ✅ | safe to retry — same final state |
| DELETE | ❌ | ✅ | gone is gone |

> ⚠️ **Never perform a write in a GET.** A convenient `GET /notes/1/delete` will eventually be hit by a link prefetcher, a crawler, or a browser cache — and data disappears with nobody having clicked anything. Deletions go in DELETE (or at minimum POST).

---

## Status codes

```python
return {"note": ...}, 201                   # created
return "", 204                              # deleted, no body
abort(404)                                  # not found
return {"errors": {...}}, 422               # validation failed
```

| Code | Meaning | Use it when |
|------|---------|-------------|
| **200** | OK | successful GET/PUT/PATCH |
| **201** | Created | POST created something |
| **204** | No Content | DELETE succeeded (empty body) |
| **302** | Found | redirect after POST |
| **400** | Bad Request | malformed request |
| **401** | Unauthorized | **not authenticated** (missing/invalid credentials) |
| **403** | Forbidden | authenticated, **not allowed** |
| **404** | Not Found | no such resource |
| **405** | Method Not Allowed | Flask sends this for you |
| **409** | Conflict | duplicate (e.g. email already registered) |
| **413** | Payload Too Large | upload over `MAX_CONTENT_LENGTH` — Flask sends it |
| **415** | Unsupported Media Type | wrong file/content type |
| **422** | Unprocessable Entity | body parsed but **failed validation** |
| **500** | Server Error | your bug — never leak details |

The families: **2xx** worked, **3xx** go elsewhere, **4xx** the *client* erred, **5xx** *you* did.

**401 vs 403** is the pair people confuse: 401 means *"I don't know who you are"*, 403 means *"I know, and no"*. FlaskNotes returns 403 when you request someone else's note — you're authenticated, just not entitled.

---

## Recap & next

- ✅ GET read · POST create (201) · PUT replace · PATCH partial · DELETE (204); 405 is automatic.
- ✅ **Safe** = no change; **idempotent** = retry-safe. Never write in a GET.
- ✅ 401 = unauthenticated, 403 = forbidden; 422 = validation; 409 = conflict; 413/415 for uploads.
- ✅ Self-check: a user submits a form twice by double-clicking. Which method makes that dangerous, and what pattern prevents it?

→ Next: **[03-2 · JSON APIs & validation](02_json_apis_validation.md)**

## Exercises

1. Assign a method + success code to: (a) log in, (b) list notes, (c) rename a note, (d) delete a note, (e) upload an avatar.

<details>
<summary>Solution</summary>

(a) `POST /auth/token` → 200 (an action, not idempotent). (b) `GET /notes` → 200. (c) `PATCH /notes/{id}` → 200 (partial). (d) `DELETE /notes/{id}` → 204. (e) `POST /avatar` → 201 (it creates a resource).
</details>
