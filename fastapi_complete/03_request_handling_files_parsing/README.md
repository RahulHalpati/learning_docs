# Section 03 · Request handling: forms, files & parsing

> **Prerequisites:** [02 · FastAPI fundamentals & Pydantic v2](../02_fastapi_fundamentals_pydantic/README.md) · **Time:** ~5 h

JSON is only half of HTTP: real backends read headers and cookies, accept browser forms and file uploads, and every one of those inputs is attacker-controlled. This section covers the rest of the request surface — multipart uploads with **UploadFile**, image validation and thumbnailing with **Pillow**, and text extraction from PDFs and Word files with **pypdf** and python-docx. linkbox pauses here: you'll build a standalone side-quest service so uploads and parsing get your full attention (the database arrives in Section 05 — this section uses local disk plus an in-memory metadata dict).

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 03-1 | [Headers, cookies & HTTP semantics](01_headers_cookies_http_semantics.md) | What else is in a request besides path/query/body — and which status code and response class do I return? |
| 03-2 | [Forms & file uploads](02_forms_and_file_uploads.md) | How do I accept multipart uploads without trusting the filename, the size claim, or my own RAM? |
| 03-3 | [Image uploads & validation](03_image_uploads_validation.md) | How do I *prove* an upload is an image, and thumbnail it without freezing the event loop? |
| 03-4 | [Document parsing](04_document_parsing.md) | How do I extract text from PDFs and DOCX without letting one document take the service down? |

## Mini-project — **dropdoc**

A standalone document-inbox API. Users upload images and documents; dropdoc validates them, derives thumbnails and extracted text, and serves everything back safely. Storage is local disk + an in-memory metadata dict — no database yet.

Requirements checklist:

- [ ] `POST /files` accepts multipart uploads of images (jpg/png/webp) and documents (pdf/docx). Deps installed with `uv add python-multipart pillow pypdf python-docx`.
- [ ] Size limit comes from settings and is enforced **while streaming chunks** — one byte past the cap → **413**. `Content-Length` is never trusted.
- [ ] Filenames are never trusted: files land on disk under a **uuid** name; the original filename is kept only as metadata. The upload dir sits outside any served/static tree.
- [ ] Images pass the full ladder: magic bytes → Pillow `verify()` + re-open → **re-encode** (kills embedded payloads, strips EXIF). Failures → **415**. A 256px thumbnail is generated with `img.thumbnail()`.
- [ ] Documents get text extracted (pypdf / python-docx) with page and word counts in metadata.
- [ ] All Pillow and parsing work runs via `run_in_threadpool` — a `GET /healthz` fired during a 200-page parse answers immediately.
- [ ] `GET /files` lists all metadata (Pydantic `FileMeta` models from the in-memory dict).
- [ ] `GET /files/{id}` serves the file with the correct `Content-Type` and a sanitized `Content-Disposition`.
- [ ] `GET /files/{id}/text` returns extracted text (404 for images and unknown ids).

## Test task (gate)

Before Section 04, pass a **seeded-vulnerabilities audit**. You receive this upload handler; it contains exactly four defects:

```python
# audit_me.py — four vulnerabilities. Find, name, fix, prove.
UPLOAD_DIR = Path("uploads")

@app.post("/upload")
async def upload(file: UploadFile):
    if file.content_type not in ("image/png", "image/jpeg", "application/pdf"):
        raise HTTPException(415, "unsupported type")
    data = await file.read()
    dest = UPLOAD_DIR / file.filename
    dest.write_bytes(data)
    pages = None
    if file.content_type == "application/pdf":
        pages = len(PdfReader(dest).pages)
    return {"name": file.filename, "size": len(data), "pages": pages}
```

The four defects, for the record:

1. **Path traversal / overwrite** — `UPLOAD_DIR / file.filename` lets a client named `../../../etc/cron.d/x` write outside the upload dir, or silently overwrite another user's file.
2. **Trusted Content-Type** — the header is a client claim. An HTML/JS file uploaded as `image/png` is stored, later served, and executes in the victim's browser: stored XSS.
3. **Unbounded read** — `await file.read()` with no cap pulls the entire body toward memory; a large upload is a denial-of-service.
4. **Sync parse on the event loop** — `PdfReader` on a 200-page PDF runs synchronously inside the `async def` handler, freezing every other request until it finishes.

**Passing looks like exactly this:**

- Each defect **named, with the attack it enables** (as above), in a short written audit.
- Each defect **fixed**: uuid names on disk (and reject filenames containing path separators or `..` with **400** as defense in depth); magic-byte check + Pillow decode + re-encode instead of trusting the header; chunked reads counted against a settings cap → **413**; parsing moved to `run_in_threadpool`.
- A **curl/httpx transcript proving each fix**: a traversal filename → 400; an HTML file uploaded as `image/png` → 415; an oversized upload → 413; and `GET /healthz` answering instantly while a big PDF parses.

Anything less — a defect fixed but not named, or named but not proven — is not a pass.

## What you'll be able to do after this section

- Read and set headers and cookies with `Annotated` params, and pick the right status code and response class for any endpoint.
- Accept multipart uploads that stream to disk under uuid names, enforcing size limits with 413 instead of trusting `Content-Length`.
- Validate images by what they *are* (magic bytes, Pillow decode, re-encode) rather than what they claim to be.
- Extract text from PDFs and DOCX off the event loop, and recognize when a job belongs in a background queue instead.
- Audit an upload handler for the classic attacks: traversal, spoofed types, memory exhaustion, event-loop freeze.

→ Start: **[03-1 · Headers, cookies & HTTP semantics](01_headers_cookies_http_semantics.md)**
