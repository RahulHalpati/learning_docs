# 03-2 · Forms & file uploads

> **Level:** Beginner→Intermediate · **Prerequisites:** [03-1 · Headers, cookies & HTTP semantics](01_headers_cookies_http_semantics.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (FastAPI 0.116 · python-multipart)

## Why this matters

File upload endpoints are a favorite attack surface: the attacker controls the filename (path traversal), the declared size (memory exhaustion), and the declared type (we deal with that lie in 03-3). Every rule in this lesson exists because skipping it enables a specific attack — and "the framework handles it" is true for parsing, but *not* for storage, size limits, or filenames. Those are on you.

---

## Why multipart exists — and why Form ≠ JSON

Files are raw bytes; JSON is text. You *could* base64 a file into a JSON string (+33% size, full buffering), but HTML solved this in the 90s: `multipart/form-data`, a body format that carries text fields and binary files side by side. Browsers send it, and FastAPI parses it — if you install the parser:

```bash
uv add python-multipart   # FastAPI's multipart/form-data parser — Form()/File() fail without it
```

Form fields are declared like body fields, but with `Form()`:

```python
from typing import Annotated
from fastapi import FastAPI, Form

app = FastAPI()

@app.post("/login")
async def login(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    return {"username": username}
```

> **One content-type owns the request.** A request body is *either* JSON *or* multipart — never both. You cannot declare a Pydantic `Body` model **and** a `File()` in the same endpoint; if a file needs structured metadata alongside it, send the metadata as `Form()` fields (or a JSON string in a form field) in the same multipart body.

---

## UploadFile anatomy

```python
from fastapi import File, UploadFile

@app.post("/files")
async def upload(file: Annotated[UploadFile, File()]):
    return {
        "filename": file.filename,          # CLIENT-SUPPLIED — a claim, never a path
        "content_type": file.content_type,  # CLIENT-SUPPLIED — a claim, never a fact
        "first_kb": len(await file.read(1024)),
    }
```

Under the hood, `UploadFile` wraps a **`SpooledTemporaryFile`**: small uploads stay in RAM, large ones spill transparently to disk. That's why you declare `UploadFile` and not `bytes = File()` — the `bytes` form reads the *entire* upload into memory, so one 2 GB upload (or ten concurrent 200 MB ones) takes the process down. `UploadFile` also gives you async methods (`await file.read(n)`, `.seek()`, `.close()`) that don't block the event loop.

---

## Streaming to disk, with a real size limit

`Content-Length` is a **client claim** — a hostile client omits it or lies, then streams forever. The only size limit that exists is the one you enforce *while reading*:

```python
import uuid
from pathlib import Path
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool

UPLOAD_DIR = Path("var/uploads")     # OUTSIDE any static/ tree the app serves
CHUNK_SIZE = 64 * 1024
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # in real code: from Settings (Section 02)

async def save_upload(file: UploadFile) -> tuple[Path, int]:
    stored_name = str(uuid.uuid4())              # WE name the file — never file.filename
    dest = UPLOAD_DIR / stored_name
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(CHUNK_SIZE):      # async read, one chunk in RAM
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                dest.unlink(missing_ok=True)             # no half-written orphans
                raise HTTPException(413, "File exceeds size limit")
            await run_in_threadpool(out.write, chunk)    # disk write off the event loop
    return dest, size
```

- **Chunked loop** — memory use is one chunk, regardless of file size. `413 Content Too Large` is the correct rejection.
- **Writes off the loop** — disk I/O is blocking; `run_in_threadpool` keeps the event loop serving other requests. (The `aiofiles` package is the popular alternative: `async with aiofiles.open(...)` — same effect, nicer syntax.)
- **Reject early too** — checking `Content-Length` up front is a nice fast-fail for *honest* clients; it just can't be your only defense.

---

## Storage discipline: the filename is an attack

`file.filename` is typed by the attacker. Use it as a path and `../../../etc/cron.d/evil` walks out of your upload dir and into the OS; even a benign-looking `report.pdf` overwrites the previous user's `report.pdf`. The rules:

- **Store under a uuid** you generated. Keep the original name as *metadata only* — for display and download headers, never for paths.
- **Upload dir outside the served tree.** If uploads land inside a static-files mount, every uploaded file is instantly a public URL — including the "image" that's actually an HTML page (the stored-XSS setup we defuse in 03-3).

```python
FILES: dict[str, dict] = {}   # in-memory metadata — the DB replaces this in Section 05

@app.post("/files", status_code=201)
async def create_file(file: Annotated[UploadFile, File()], title: Annotated[str, Form()] = ""):
    path, size = await save_upload(file)
    meta = {"id": path.name, "original_name": file.filename or "unnamed",
            "content_type": file.content_type, "size": size, "title": title}
    FILES[path.name] = meta
    return meta
```

Multiple files? Declare `files: Annotated[list[UploadFile], File()]` and loop — each element is a full `UploadFile`.

---

## Serving files back

`FileResponse` streams from disk and sets `Content-Length`; you set the type and the disposition:

```python
from fastapi.responses import FileResponse

@app.get("/files/{file_id}")
async def download(file_id: str):
    meta = FILES.get(file_id)
    if meta is None:
        raise HTTPException(404)
    # Sanitize before it goes into a header: strip any path, kill quotes/CRLF
    safe_name = Path(meta["original_name"]).name.replace('"', "").replace("\r", "").replace("\n", "")
    return FileResponse(
        UPLOAD_DIR / file_id,
        media_type=meta["content_type"],        # after 03-3, this is a VERIFIED type
        filename=safe_name,                     # → Content-Disposition: attachment; filename="..."
    )
```

- **`attachment` vs `inline`** — `attachment` (what `filename=` produces) forces a download; `content_disposition_type="inline"` asks the browser to render in-tab. Serve anything user-uploaded as `attachment` unless you've *verified* it's safe to render — an inline HTML file executes its scripts on your origin.
- **Sanitize names going into headers** — the original filename is user input; unescaped quotes or CR/LF characters in a header value are a header-injection vector. Strip to the base name and drop the dangerous characters.

---

## Static assets vs uploads: `StaticFiles`

For files *you* ship — a favicon, docs assets, a JS bundle — don't write endpoints at all; mount a static directory:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
# GET /static/logo.png now serves static/logo.png with correct type + ETag caching
```

Keep the distinction sharp, because blurring it is a classic vulnerability:

- **`StaticFiles` is for trusted, developer-owned assets.** It serves whatever is in the directory, as-is, renderable inline.
- **User uploads never go in the mounted directory.** An uploaded HTML/SVG file served inline from your origin is stored XSS (03-3 makes this concrete). Uploads live *outside* any static mount and come back only through your endpoint — where you control verification, `Content-Disposition`, and authorization.

---

## Recap & next

- ✅ Multipart carries text + binary together; `uv add python-multipart` or `Form()`/`File()` won't work. One content-type owns the request — no JSON `Body` mixed with `File`.
- ✅ `UploadFile` (spooled temp file, async API) beats `bytes = File()`, which buffers everything in RAM.
- ✅ Size limits are enforced **while reading chunks** → 413; `Content-Length` is a claim.
- ✅ uuid on disk, original filename as metadata only, upload dir outside the served tree — each rule blocks a named attack.
- ✅ `FileResponse` + sanitized `Content-Disposition`; `attachment` for anything you haven't verified.
- ✅ Self-check: which *two distinct attacks* does storing under a uuid (instead of `file.filename`) prevent?

→ Next: **[03-3 · Image uploads & validation](03_image_uploads_validation.md)**

## Exercises

1. Break the naive version on purpose: write an endpoint that saves to `UPLOAD_DIR / file.filename`, then upload with `curl -F 'file=@x.txt;filename=../escaped.txt'`. Where did the file land? Fix it with the uuid pattern and confirm the traversal name is now inert.

<details>
<summary>Solution</summary>

The file lands in `UPLOAD_DIR`'s *parent* — `Path("var/uploads") / "../escaped.txt"` resolves to `var/escaped.txt`, outside the upload dir. With more `../` segments it reaches anywhere the process can write. After switching to `dest = UPLOAD_DIR / str(uuid.uuid4())`, the client's filename never touches the path — it's stored as metadata, and the same curl lands harmlessly as `var/uploads/<uuid>`. Belt-and-braces: also reject filenames containing `/`, `\`, or `..` with a 400, so hostile intent is logged rather than silently defused.
</details>

2. Extend `POST /files` to accept up to 5 files plus a required `album: str` form field in one request, rejecting the 6th file with a 400. Return the list of stored ids.

<details>
<summary>Solution</summary>

```python
@app.post("/albums", status_code=201)
async def upload_album(
    files: Annotated[list[UploadFile], File()],
    album: Annotated[str, Form()],
):
    if len(files) > 5:
        raise HTTPException(400, "Max 5 files per album")
    ids = []
    for f in files:
        path, size = await save_upload(f)          # each one streamed + capped
        FILES[path.name] = {"id": path.name, "album": album,
                            "original_name": f.filename or "unnamed", "size": size}
        ids.append(path.name)
    return {"album": album, "ids": ids}
```

Files and form fields coexist because both live in the same multipart body — this is exactly the case where you *can't* use a JSON `Body` model for `album`.
</details>

3. Prove the 413 works even when the client lies: send a large file with `curl --header "Content-Length: 10"`... actually, curl won't let you understate it — instead upload a file just over your cap and confirm (a) the response is 413 and (b) no partial file remains in the upload dir.

<details>
<summary>Solution</summary>

```bash
dd if=/dev/zero of=big.bin bs=1M count=11          # 11 MB > 10 MB cap
curl -i -F file=@big.bin http://localhost:8000/files
ls var/uploads/
```

The response is `413`, and the dir has no new file — because `save_upload` counts bytes *as they arrive* and calls `dest.unlink()` before raising. The lesson: the enforcement point is the read loop, not any header, so it holds no matter what the client claims.
</details>
