# 03-3 · Image uploads & validation

> **Level:** Beginner→Intermediate · **Prerequisites:** [03-2 · Forms & file uploads](02_forms_and_file_uploads.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (FastAPI 0.116 · Pillow)

## Why this matters

"It says it's a PNG" is not a fact — it's a client claim, and treating it as truth is one of the most exploited upload bugs there is. An attacker uploads an HTML file with `Content-Type: image/png`; your server stores it, later serves it, and the victim's browser runs its JavaScript on *your* origin — stored XSS. Polyglot files (valid image *and* valid HTML/JS at once) sneak past extension and even magic-byte checks. The only thing that ends the argument is decoding the bytes as an image and re-encoding them yourself. This lesson builds that ladder.

```bash
uv add pillow   # imports as `PIL`
```

---

## The validation ladder

Each rung is stronger than the last. Real code stacks several — but know what each is worth.

**(a) Allowlist extension + declared MIME — weakest.** Both are attacker-controlled strings. Useful only as a fast, cheap first filter, never as a security boundary:

```python
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
if file.content_type not in ALLOWED:      # rejects honest mistakes; a hostile client just lies
    raise HTTPException(415, "unsupported media type")
```

**(b) Magic bytes — better.** The first few bytes of a real file identify its true format regardless of extension or header. `\x89PNG` for PNG, `\xff\xd8\xff` for JPEG, `RIFF....WEBP` for WebP:

```python
SIGNATURES = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpeg"}

def sniff(head: bytes) -> str | None:
    if head[8:12] == b"WEBP" and head[:4] == b"RIFF":
        return "webp"
    return next((fmt for sig, fmt in SIGNATURES.items() if head.startswith(sig)), None)
```

Magic bytes defeat a plain renamed `.html`, but a polyglot can carry a valid PNG header *and* a script payload. So we keep going.

**(c) Decode with Pillow — strong.** If the bytes don't parse as a real image, they aren't one. Mind the gotcha: **`verify()` consumes the file handle**, so you must re-open before doing anything else:

```python
from io import BytesIO
from PIL import Image, UnidentifiedImageError

def decode_check(data: bytes) -> str:
    try:
        Image.open(BytesIO(data)).verify()      # structural check — but INVALIDATES the object
    except (UnidentifiedImageError, OSError):
        raise HTTPException(415, "not a valid image")
    img = Image.open(BytesIO(data))             # MUST re-open: the verified one is now unusable
    return img.format                           # "PNG" / "JPEG" / "WEBP" — the TRUE format
```

**(d) Re-encode — strongest, and what you should ship.** Decode to a pixel buffer and write a *brand-new* file. This is decisive: any HTML, script, or polyglot payload riding along in the original is simply not part of the pixels, so it does not survive re-encoding. It also strips **EXIF metadata** — which matters for privacy, because phone photos embed GPS coordinates and you do not want to silently republish where a user lives:

```python
def reencode(data: bytes, fmt: str = "PNG") -> bytes:
    img = Image.open(BytesIO(data))
    img = img.convert("RGB")            # drop alpha/palette quirks; also flattens to raw pixels
    out = BytesIO()
    img.save(out, format=fmt)           # a FRESH file from pixels only — payloads and EXIF gone
    return out.getvalue()
```

---

## Decompression bombs

A 40 KB PNG can legally decode to 40,000 × 40,000 pixels — ~6 GB in RAM. That's a decompression bomb: tiny on disk, catastrophic when opened. Pillow guards against it, but you should set the ceiling explicitly:

```python
from PIL import Image

Image.MAX_IMAGE_PIXELS = 24_000_000     # ~24 MP cap; over this Pillow raises DecompressionBombError

# Pillow WARNS at MAX_IMAGE_PIXELS and RAISES at 2× it. To fail hard, turn the warning into an error:
import warnings
warnings.simplefilter("error", Image.DecompressionBombWarning)
```

Catch `Image.DecompressionBombError` alongside your other decode errors and return 415 — a bomb is a malformed-for-your-purposes image, not a server error.

---

## Thumbnails: `thumbnail()` vs `resize()`

Use **`img.thumbnail()`** — it scales to fit *within* a box while preserving aspect ratio, and only ever shrinks. `resize()` forces exact dimensions and will distort a portrait into a square:

```python
def make_thumbnail(img: Image.Image, box: int = 256) -> bytes:
    img.thumbnail((box, box))           # in place; keeps aspect ratio, never upscales
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
```

---

## All of it is CPU-bound — get it off the event loop

Decoding, re-encoding, and thumbnailing are pure CPU work in C. Run them directly in an `async def` handler and they **block the event loop** — every other request, including `/healthz`, waits behind one image. Wrap the CPU work in `run_in_threadpool`:

```python
from fastapi.concurrency import run_in_threadpool

def process_image(data: bytes) -> dict:                 # plain sync fn — all the CPU work
    decode_check(data)                                  # raises 415 on non-images / bombs
    safe = reencode(data, fmt="PNG")                    # fresh file: payloads + EXIF gone
    width, height = Image.open(BytesIO(safe)).size
    thumb = make_thumbnail(Image.open(BytesIO(safe)))
    return {"safe": safe, "thumb": thumb, "format": "PNG", "width": width, "height": height}

@app.post("/images", status_code=201)
async def upload_image(file: Annotated[UploadFile, File()]):
    data = await read_capped(file)                      # same chunked-read + 413 cap as 03-2, but into bytes
    result = await run_in_threadpool(process_image, data)   # CPU work on a worker thread
    # persist result["safe"] and result["thumb"] under uuid names; store dims/format as metadata
    return {"width": result["width"], "height": result["height"], "format": result["format"]}
```

> **When even the thread pool isn't enough.** A thread pool has a fixed size; a flood of large images can exhaust it and queue requests. For bulk processing, very large images, or anything slow, hand the job to a background worker and return `202 Accepted` immediately. The course wires this up with Arq in [Section 08 · Redis, caching & jobs](../08_redis_caching_jobs/README.md) — forward-reference for now.

---

## Recap & next

- ✅ The declared type and extension are claims; validate by *decoding the bytes*.
- ✅ Ladder: allowlist (weak) → magic bytes (better) → Pillow `verify()`+re-open (strong) → **re-encode (ship this)**.
- ✅ `verify()` invalidates the handle — always re-open before using the image.
- ✅ Re-encoding destroys embedded payloads *and* strips EXIF/GPS; set `Image.MAX_IMAGE_PIXELS` to stop decompression bombs → 415.
- ✅ `thumbnail()` preserves aspect ratio; `resize()` distorts. All Pillow work goes through `run_in_threadpool`, never inline.
- ✅ Self-check: an upload passes the magic-byte check but is a polyglot carrying a `<script>`. Which rung of the ladder finally neutralizes it, and why?

→ Next: **[03-4 · Document parsing](04_document_parsing.md)**

## Exercises

1. Demonstrate the stored-XSS setup and the fix. Save `<img src=x onerror=alert(1)>` as `evil.png`, upload it to a handler that trusts `content_type` and serves inline, and observe it would render as HTML. Then route it through `process_image` and show it's rejected at `decode_check` with 415.

<details>
<summary>Solution</summary>

The naive handler stores `evil.png` verbatim and serves it with `Content-Type: image/png, Content-Disposition: inline` — but browsers sniff, and if the file is really HTML the script runs on your origin. Through the ladder, `Image.open(...).verify()` raises `UnidentifiedImageError` because the bytes aren't a decodable image → 415. Even a *polyglot* (real PNG header + trailing HTML) is defused: `reencode` writes a fresh file from pixels only, so the trailing HTML never reaches disk. Serving `attachment` instead of `inline` is the belt to this braces.
</details>

2. Prove the re-encode strips EXIF. Take a JPEG with GPS EXIF (`exiftool` shows the coordinates), run it through `reencode`, and confirm the output has no GPS tags.

<details>
<summary>Solution</summary>

```python
from PIL import Image
from PIL.ExifTags import GPSTAGS

before = Image.open("geotagged.jpg").getexif()
print("before:", bool(before))                # has EXIF/GPS

clean = reencode(open("geotagged.jpg", "rb").read(), fmt="JPEG")
after = Image.open(BytesIO(clean)).getexif()
print("after:", dict(after))                  # {} — re-encode wrote pixels only
```

`img.save()` from a decoded pixel buffer emits no EXIF unless you explicitly pass it, so GPS coordinates (and camera serials, timestamps) are gone. This is a privacy control, not just security — you avoid silently republishing where a user took the photo.
</details>

3. Trigger and handle a decompression bomb. Set `Image.MAX_IMAGE_PIXELS = 1_000_000`, upload a legitimate 4000×3000 image (12 MP), and confirm it's rejected with 415 rather than eating RAM.

<details>
<summary>Solution</summary>

With the cap at 1 MP, opening a 12 MP image raises `Image.DecompressionBombError` (or the warning-turned-error). Catch it in `decode_check` alongside `UnidentifiedImageError`/`OSError` and map to 415:

```python
except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
    raise HTTPException(415, "image too large to decode")
```

The point: the limit fires *before* Pillow allocates the full pixel buffer, so a 40 KB bomb can't turn into 6 GB of RAM. Set the real cap to what your product actually needs (24 MP is generous for user photos).
</details>
