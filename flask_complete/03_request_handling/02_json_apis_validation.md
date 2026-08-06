# 03-2 · JSON APIs & validation

> **Level:** Beginner → Intermediate · **Prerequisites:** [01-3 · Request & response](../01_foundations/03_request_and_response.md)
> **Time:** 45 min · **Verified:** 2026-07-29 (Flask 3.1.3)

## Why this matters

Unlike FastAPI, **Flask does not validate anything for you**. `request.get_json()` hands you whatever the client sent — including `None`, wrong types, and missing keys. Validation is your job, and skipping it is how Flask APIs end up with 500s and corrupt data. This lesson covers doing it by hand (always available) and with a library (when it grows).

---

## Reading JSON safely

```python
from flask import request

@app.post("/api/notes")
def create():
    data = request.get_json(silent=True) or {}      # never raises, never None
    ...
```

- **`silent=True`** returns `None` instead of raising a 415/400 when the body isn't JSON.
- **`or {}`** means the rest of your code can assume a dict.

That one line prevents the most common Flask API crash.

---

## Hand-rolled validation

For a few fields, explicit checks are clear and dependency-free — collect *all* errors rather than failing on the first:

```python
@app.post("/api/notes")
def create():
    data = request.get_json(silent=True) or {}
    errors = {}
    if not (data.get("title") or "").strip():
        errors["title"] = "required"
    if "priority" in data and data["priority"] not in ("low", "high"):
        errors["priority"] = "invalid"
    if errors:
        return {"errors": errors}, 422
    return {"id": 1, **data}, 201
```

**Output (real run):**
```
POST {"title": "Buy milk"}                      ->  201  {'id': 1, 'title': 'Buy milk'}
POST {"title": "", "priority": "urgent"}        ->  422  {'errors': {'title': 'required',
                                                                    'priority': 'invalid'}}
```

Returning **all** the problems at once (not just the first) is a real usability win — the client fixes everything in one round trip.

> **Tip — a consistent error shape.** Pick one envelope (`{"errors": {...}}` or `{"error": {"message": ...}}`) and use it everywhere, including your error handlers ([07-1](../07_errors_logging_cors/01_error_handling.md)). Clients branch on structure; inconsistency there is a constant source of bugs. FlaskNotes uses `{"error": {"message", "status"}}`.

---

## When to reach for a library

Hand validation stops scaling around a dozen fields or nested objects. Two industry-standard options:

| Library | Style | Good when |
|---------|-------|-----------|
| **marshmallow** | schema `load()`/`dump()` | classic Flask stacks; input and output shapes differ |
| **pydantic** | typed models | you want type hints + editor autocomplete (and speed) |

```python
# marshmallow — the traditional Flask choice
from marshmallow import Schema, fields, ValidationError

class NoteSchema(Schema):
    title = fields.Str(required=True, validate=lambda s: len(s.strip()) > 0)
    body = fields.Str(load_default="")

@app.post("/api/notes")
def create():
    try:
        data = NoteSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return {"errors": exc.messages}, 422       # marshmallow builds the error dict
    ...
```

```python
# pydantic — if you prefer typed models
from pydantic import BaseModel, ValidationError, Field

class NoteIn(BaseModel):
    title: str = Field(min_length=1)
    body: str = ""
```

Both give you the same 422-with-details result; pick one and be consistent. (**flask-smorest** goes further, combining marshmallow with automatic OpenAPI docs — worth knowing if you build many endpoints.)

---

## Returning JSON

Returning a dict auto-serializes. `jsonify()` is the explicit form and takes keyword arguments:

```python
return jsonify(items=[...], total=3, page=1)          # explicit
return {"id": 1}, 201                                  # shorthand + status
```

For model objects, give them a `to_dict()` (as FlaskNotes' `Note` does) so serialization lives in one place and can't accidentally leak a password hash.

---

## Recap & next

- ✅ Flask validates **nothing** — `request.get_json(silent=True) or {}` then check it yourself.
- ✅ Collect all errors and return **422** with a structured body; keep one error shape app-wide.
- ✅ Scale up with **marshmallow** (classic) or **pydantic** (typed); flask-smorest adds OpenAPI.
- ✅ Serialize models via an explicit `to_dict()` so secrets can't leak.
- ✅ Self-check: what does `get_json()` do on a non-JSON body, and how does `silent=True` change it?

→ Next: **[03-3 · Forms, files & images](03_forms_files_images.md)**

## Exercises

1. Add validation to a `PATCH /api/notes/<id>`: reject an empty `title` if provided, ignore unknown keys, and return 422 with details.

<details>
<summary>Solution</summary>

Check `if "title" in data` before validating (so an omitted title is fine but an empty one is 422), and only copy known keys onto the model — never `for k, v in data.items(): setattr(note, k, v)`, which would let a client set `user_id` and steal another user's note. That mass-assignment trap is exactly why you whitelist fields.
</details>
