# 03-4 · Document parsing

> **Level:** Beginner→Intermediate · **Prerequisites:** [03-3 · Image uploads & validation](03_image_uploads_validation.md)
> **Time:** ~40 min · **Verified:** 2026-08-07 (FastAPI 0.116 · pypdf · python-docx)

## Why this matters

Extracting text from an uploaded PDF or Word doc looks harmless — until you remember the document was written by whoever uploaded it. A crafted PDF can be built to explode parse time or memory (a parser-level decompression bomb); a 200-page report parsed inside an `async` handler freezes every other request while it runs. The same three defenses from the last two lessons apply here: gate the size, run the CPU work off the event loop, and know when the job is too big to do in the request at all.

```bash
uv add pypdf python-docx   # PDF and DOCX readers; both pure-Python
```

---

## PDFs with pypdf — and its honest limits

```python
from pypdf import PdfReader

def extract_pdf(path: str) -> tuple[str, int]:
    reader = PdfReader(path)
    pages = reader.pages
    text = "\n".join(page.extract_text() or "" for page in pages)  # "" guards blank/image pages
    return text, len(pages)
```

Know what this does *not* do:

- **Layout is lost.** `extract_text()` gives you a linear stream, not columns or tables as you see them. Fine for search and word counts; not for reconstructing a form.
- **Scanned PDFs yield nothing.** A PDF that is just a photo of a page has no text layer — `extract_text()` returns `""`. Extracting that text needs **OCR** (optical character recognition, e.g. `pytesseract` over rendered page images). OCR is slow, heavy, and its own project — know it exists; do not build it here.

---

## DOCX with python-docx

Word documents are structured — you walk paragraphs and tables rather than a flat stream:

```python
from docx import Document

def extract_docx(path: str) -> tuple[str, int]:
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs if p.text]
    for table in doc.tables:                              # tables live outside paragraphs
        for row in table.rows:
            parts.append("\t".join(cell.text for cell in row.cells))
    text = "\n".join(parts)
    return text, len(doc.paragraphs)                      # docx has no fixed "pages" — count paragraphs
```

---

## Plain text and encoding pitfalls

Never assume UTF-8 and never let a bad byte crash the request. Decode defensively:

```python
def extract_txt(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")   # bad bytes → U+FFFD, never a UnicodeDecodeError
```

If you genuinely need to *detect* the encoding of arbitrary uploads (legacy exports, non-UTF-8 CSVs), the `chardet` / `charset-normalizer` library guesses it — but `errors="replace"` on UTF-8 is right for the overwhelming majority of uploads and adds no dependency.

---

## The extraction endpoint — with a size gate, a thread pool, and truncation

```python
from fastapi.concurrency import run_in_threadpool

MAX_TEXT_CHARS = 500_000     # cap what we store/return — a huge doc shouldn't produce a huge response

def extract_any(path: str, content_type: str) -> tuple[str, int]:
    if content_type == "application/pdf":
        return extract_pdf(path)
    if content_type.endswith("wordprocessingml.document"):    # docx
        return extract_docx(path)
    raise HTTPException(415, "no text extractor for this type")

@app.get("/files/{file_id}/text")
async def get_text(file_id: str):
    meta = FILES.get(file_id)
    if meta is None:
        raise HTTPException(404)
    if meta["content_type"].startswith("image/"):
        raise HTTPException(404, "no text for images")        # images went through 03-3, not here
    # CPU-bound parse → worker thread, so the event loop keeps serving
    text, pages = await run_in_threadpool(
        extract_any, str(UPLOAD_DIR / file_id), meta["content_type"]
    )
    words = len(text.split())
    return {"pages": pages, "words": words, "truncated": len(text) > MAX_TEXT_CHARS,
            "text": text[:MAX_TEXT_CHARS]}
```

- **Size gate** — the upload was already capped in 03-2, so an unbounded document never reaches this parser in the first place.
- **`run_in_threadpool`** — the whole reason the endpoint stays responsive under a slow parse (next section).
- **Truncation** — cap the extracted text so a legitimately huge document doesn't produce a multi-megabyte JSON response.

---

## Sync parse in an async handler = frozen event loop

This is the defect worth *seeing*, not just reading about. Put a synchronous `PdfReader(...).pages` call directly in an `async def` and fire two requests: a slow parse and a `/healthz`.

```python
# WRONG — blocks the event loop for the whole parse
@app.get("/files/{file_id}/text")
async def get_text_bad(file_id: str):
    text = "\n".join(p.extract_text() or "" for p in PdfReader(...).pages)  # ← 200 pages = seconds of block
    return {"text": text}
```

**Symptom:** while a 200-page PDF parses, `curl http://localhost:8000/healthz` *hangs* — not because health is broken, but because the single event-loop thread is stuck decoding a PDF and can't get to any other request. One user's upload has taken the whole service hostage.

**Fix:** `await run_in_threadpool(extract_any, ...)`. The parse moves to a worker thread, the event loop is free, and `/healthz` answers instantly while the PDF churns in the background. This is the exact scenario the mini-project's gate makes you demonstrate.

> **When extraction belongs in a background job.** The thread pool handles *occasional* slow parses. But large files, OCR, or batch processing will exhaust a fixed pool and queue requests. At that point extraction shouldn't happen in the request at all: accept the upload, return `202 Accepted` with a job id, and let a worker parse it. The course builds this with Arq in [Section 08 · Redis, caching & jobs](../08_redis_caching_jobs/README.md).

---

## Modeling the metadata with Pydantic

Everything an endpoint returns is a Pydantic v2 model — including derived counts. Use a **computed field** for values you don't want to store but want in the response:

```python
from pydantic import BaseModel, ConfigDict, computed_field

class FileMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_name: str
    content_type: str
    size: int
    pages: int | None = None       # None for images / txt
    word_count: int | None = None

    @computed_field                # appears in the response, not stored on the model's inputs
    @property
    def kind(self) -> str:
        return "image" if self.content_type.startswith("image/") else "document"
```

`GET /files` returns `list[FileMeta]` built from the in-memory dict; in Section 05 the same models will be built from database rows instead — the API shape doesn't change.

---

## Recap & next

- ✅ pypdf iterates pages and `extract_text()`s them — but loses layout and returns nothing for scanned PDFs (that's OCR territory; don't build it here).
- ✅ python-docx walks paragraphs *and* tables; decode plain text with `errors="replace"` to survive bad bytes.
- ✅ A synchronous parse in an `async` handler freezes the event loop — provable by a hanging `/healthz`; the fix is `run_in_threadpool`.
- ✅ Gate size, truncate output, and push big/OCR/batch jobs to a background worker (Arq, Section 08).
- ✅ Model responses with Pydantic v2 `FileMeta` + `computed_field`; the API shape survives the move to a real DB.
- ✅ Self-check: your `/healthz` hangs whenever someone uploads a big PDF. What's the one-line cause, and the one-line fix?

→ Next: **[04 · Dependency injection & app structure](../04_dependency_injection_app_structure/README.md)**

## Exercises

1. Reproduce the frozen event loop, then fix it. Write the WRONG version above, upload a large PDF, and — *during* the parse — time a `curl /healthz`. Then switch to `run_in_threadpool` and time it again.

<details>
<summary>Solution</summary>

With the sync version, `time curl localhost:8000/healthz` fired mid-parse blocks for as long as the parse takes (seconds for a big PDF) — the event loop thread is busy decoding. After `await run_in_threadpool(extract_any, ...)`, the same `/healthz` returns in milliseconds while the PDF parses on a worker thread. Nothing about the health endpoint changed; the only difference is *where* the CPU work runs. This is the whole async-correctness lesson in one measurement.
</details>

2. Add page/word counts to `FileMeta` at upload time (not lazily). Extend `POST /files` so a PDF's `pages` and `word_count` are computed once — off the event loop — and stored, so `GET /files` shows them without re-parsing.

<details>
<summary>Solution</summary>

```python
@app.post("/files", status_code=201)
async def create_file(file: Annotated[UploadFile, File()]):
    path, size = await save_upload(file)               # 03-2: chunked + 413 cap
    meta = {"id": path.name, "original_name": file.filename or "unnamed",
            "content_type": file.content_type, "size": size}
    if file.content_type == "application/pdf":
        text, pages = await run_in_threadpool(extract_pdf, str(path))  # once, off the loop
        meta |= {"pages": pages, "word_count": len(text.split())}
    FILES[path.name] = meta
    return FileMeta.model_validate(meta)
```

Parsing at upload trades a slower upload for instant listings, and the parse still runs in the thread pool so it doesn't block. For big files you'd defer even this to a background job (Section 08) and let `GET /files` show `pages: null` until the worker fills it in.
</details>

3. Handle the scanned-PDF case gracefully: detect when `extract_text()` yields near-nothing across all pages and return a clear `"needs_ocr": true` flag instead of an empty string.

<details>
<summary>Solution</summary>

```python
def extract_pdf(path: str) -> tuple[str, int]:
    reader = PdfReader(path)
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    return text, len(reader.pages)

# in the endpoint:
text, pages = await run_in_threadpool(extract_pdf, str(UPLOAD_DIR / file_id))
needs_ocr = pages > 0 and len(text.strip()) < 10 * pages   # heuristic: <10 chars/page ≈ image-only
return {"pages": pages, "words": len(text.split()), "needs_ocr": needs_ocr, "text": text[:MAX_TEXT_CHARS]}
```

You're not building OCR — you're being honest that this PDF has no text layer, so a client knows the empty result is expected, not a bug. Wiring in `pytesseract` would be a background job (slow, heavy), never inline.
</details>
