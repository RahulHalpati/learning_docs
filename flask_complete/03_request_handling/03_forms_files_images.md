# 03-3 · Forms, files & images

> **Level:** Beginner → Intermediate · **Prerequisites:** [02-2 · Static files & flash messages](../02_templates_and_static/02_static_and_forms.md)
> **Time:** 50 min · **Verified:** 2026-07-29 (Flask 3.1.3, Werkzeug 3.1.8)

## Why this matters

HTML forms and **file uploads** are where a lot of Flask apps get insecure. An unchecked upload endpoint lets an attacker fill your disk, overwrite files via a crafted filename, or store something nasty for other users to download. Flask gives you the tools; you have to use them deliberately.

---

## Form data

An HTML form POSTs `application/x-www-form-urlencoded`; read it from `request.form`:

```python
@app.post("/login")
def login():
    return {"user": request.form.get("username"),
            "has_pw": bool(request.form.get("password"))}
```

**Output (real run):**
```
{'user': 'ada', 'has_pw': True}
```

`request.form.get(...)` (rather than `request.form[...]`) returns `None` instead of raising a 400 when a field is missing — you decide the error.

> **`request.args` vs `request.form` vs `request.get_json()`** — query string vs form body vs JSON body. Three different places; Flask never merges them for you.

---

## File uploads

A form with files must set `enctype="multipart/form-data"`:

```html
<form method="post" enctype="multipart/form-data">
  <input name="title" required>
  <input type="file" name="image" accept="image/*">
  <button>Save</button>
</form>
```

Files arrive in `request.files`:

```python
from pathlib import Path
from werkzeug.utils import secure_filename

ALLOWED = {"png", "jpg", "jpeg", "gif"}

@app.post("/upload")
def upload():
    f = request.files.get("image")
    if not f or not f.filename:
        return {"error": "no file"}, 400
    ext = Path(f.filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED:                                  # 1. check the type
        return {"error": f"type .{ext} not allowed"}, 415
    safe = secure_filename(f.filename)                      # 2. sanitize the name
    f.save(app.config["UPLOAD_FOLDER"] / safe)
    return {"saved": safe}, 201
```

**Output (real run):**
```
POST photo.png  ->  201  {'saved': 'photo.png', 'bytes': 40}
POST notes.txt  ->  415
```

### The three defenses

**1. `secure_filename()` — never trust the client's filename.**

**Output (real run):**
```
secure_filename("../../etc/passwd")  ->  'etc_passwd'
secure_filename("my photo!.PNG")     ->  'my_photo.PNG'
```

Without it, a filename of `../../etc/passwd` would let an attacker write **outside** your upload folder — a path-traversal hole. `secure_filename` strips directory components and dangerous characters.

**2. `MAX_CONTENT_LENGTH` — cap the size.**

```python
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024      # 2 MB
```

Flask rejects anything larger before your view runs:

**Output (real run, 5 KB body against a 1 KB cap):**
```
413   (Payload Too Large)
```

Without a cap, one request can exhaust your memory or disk.

**3. Check the extension *and* know its limit.** An extension (or the client-supplied `content_type`) is a *hint*, not proof — a `.png` can contain anything. For real image handling, verify the bytes by opening it with Pillow (`Image.open(f).verify()`) and reject what won't parse.

> ⚠️ **Generate your own filename in production.** FlaskNotes stores `f"{uuid.uuid4().hex}{suffix}"` — this kills collisions (two users uploading `photo.png`), stops filename guessing, and removes any remaining injection risk. Keep the original name in the database if you need to show it.

---

## Serving uploads back

Never serve the upload directory statically. Use `send_from_directory`, which safely resolves the filename inside the folder:

```python
from flask import send_from_directory

@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
```

Then in a template: `<img src="{{ url_for('web.uploaded_file', filename=note.image) }}">`.

`send_from_directory` refuses to escape the base folder, so a crafted `filename` can't read `/etc/passwd`. For user-private files, add an ownership check in the view before serving.

---

## Recap & next

- ✅ `request.form` for form fields, `request.files` for uploads; the form needs `enctype="multipart/form-data"`.
- ✅ Three defenses: **`secure_filename`** (path traversal), **`MAX_CONTENT_LENGTH`** (→ automatic **413**), **extension/content checks** (→ 415).
- ✅ Better still: store under a **generated UUID name**; keep the original name in the DB.
- ✅ Serve uploads with **`send_from_directory`**, never by exposing the folder.
- ✅ Self-check: what does `secure_filename("../../etc/passwd")` return, and what attack does that stop?

→ Next: **[04 · App structure](../04_app_structure/README.md)**

## Exercises

1. Extend the upload to store a UUID filename, keep the original in a dict, and serve it back via `send_from_directory`. Verify a `.txt` gets 415 and an oversized file gets 413.

<details>
<summary>Solution</summary>

That's exactly FlaskNotes' `save_upload()` in `app/blueprints/web.py`: validate the extension → `secure_filename` → `uuid4().hex + suffix` → save → store the name on the model. Its test suite asserts both the 415 and the successful round-trip through `/uploads/<filename>`.
</details>
