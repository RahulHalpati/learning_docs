# 03-1 · Headers, cookies & HTTP semantics

> **Level:** Beginner→Intermediate · **Prerequisites:** [02 · FastAPI fundamentals & Pydantic v2](../02_fastapi_fundamentals_pydantic/README.md)
> **Time:** ~35 min · **Verified:** 2026-08-07 (FastAPI 0.116 · Python 3.12+)

## Why this matters

Path, query, and body are where the data lives — but headers and cookies are where identity, caching, content negotiation, and security live, and status codes are the contract your API makes with every client and proxy. Get the semantics wrong (a POST that a retry duplicates, a redirect that silently drops the request body) and clients break in ways no validator catches. This lesson gives you the rest of the HTTP vocabulary before we start accepting files — which will need every bit of it.

---

## Header parameters

Declare headers like any other param — with `Annotated` and `Header()`. FastAPI converts Python underscores to HTTP hyphens automatically (`user_agent` ↔ `User-Agent`), because hyphens aren't valid in Python names:

```python
from typing import Annotated
from fastapi import FastAPI, Header

app = FastAPI()

@app.get("/whoami")
async def whoami(
    user_agent: Annotated[str | None, Header()] = None,    # reads "User-Agent"
    x_request_id: Annotated[str | None, Header()] = None,  # reads "X-Request-ID"
):
    return {"user_agent": user_agent, "request_id": x_request_id}
```

- **Headers are optional by default in HTTP** — model that with `str | None` and a default, and return 400/422 yourself only when a header is truly required.
- Declared headers show up in the OpenAPI docs and get validated — a `Annotated[int, Header()]` rejects garbage for free.

---

## Cookies: reading and setting

Reading is symmetrical — `Cookie()` instead of `Header()`. Setting means asking FastAPI for the `Response` object and calling `set_cookie`:

```python
from fastapi import Cookie, Response

@app.get("/visits")
async def visits(response: Response, visits: Annotated[int, Cookie()] = 0):
    visits += 1
    response.set_cookie(
        "visits", str(visits),
        httponly=True,    # JavaScript can't read it → an XSS can't steal it
        samesite="lax",   # not sent on cross-site POSTs → blunts CSRF
        secure=True,      # HTTPS only — never leaks over plain HTTP
        max_age=60 * 60 * 24,
    )
    return {"visits": visits}
```

> **Preview — Section 07.** Those three flags are not decoration. `httponly` + `samesite` + `secure` is the minimum for any cookie that identifies a user: without them, a script injection reads the session, a hostile site replays it, or a coffee-shop network sniffs it. Section 07 builds real session security on exactly this foundation — for now, just never set an identifying cookie without all three.

---

## The `Request` object — when declared params aren't enough

Sometimes you need the raw request: the client IP for rate limiting, the full URL for building links, the exact body bytes for webhook signature checks.

```python
from fastapi import Request

@app.post("/webhook")
async def webhook(request: Request):
    raw = await request.body()            # exact bytes — signatures hash these, not the parsed JSON
    client_ip = request.client.host       # behind a proxy this is the proxy's IP (Section 09 fixes that)
    return {"url": str(request.url), "ip": client_ip, "bytes": len(raw)}
```

Reach for `Request` **only when you need the raw material**. Declared params win everywhere else: they validate, they type-convert, and they document themselves in OpenAPI. A handler full of `request.headers.get(...)` calls is a handler with no schema — invisible to your docs and to every validator.

---

## Method semantics: idempotency is a promise

| Method | Idempotent? | Meaning |
|--------|-------------|---------|
| GET | ✅ | Read — no side effects at all |
| PUT | ✅ | Replace the whole resource; doing it twice = same result |
| DELETE | ✅ | Gone is gone; a second DELETE changes nothing |
| PATCH | ❌ (by default) | Partial update — only the fields sent |
| POST | ❌ | Create / act — doing it twice does it twice |

Why this matters: **networks retry**. A client sends POST /orders, the response is lost, the client retries — and the customer is charged twice, *unless* you designed for it. Idempotent methods are safe to retry blindly; POST is not, which is why payment APIs demand idempotency keys and why "just use POST for everything" is a production bug waiting for a flaky network.

---

## Choosing status codes

```python
from fastapi import status

@app.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(response: Response) -> dict:
    item_id = "42"
    response.headers["Location"] = f"/items/{item_id}"  # 201 should say WHERE it was created
    return {"id": item_id}

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str) -> None:
    return None                                          # 204 = success, body is empty by definition
```

- **200** — generic success with a body.
- **201 + `Location`** — created; the header points at the new resource.
- **204** — success, nothing to say (deletes, empty updates). Never return a body with it.
- **303 See Other** — the post/redirect/get pattern: after a form POST, redirect the browser to a GET so a refresh doesn't resubmit the form.
- **307 vs 308** — both preserve the method and body across the redirect (307 temporary, 308 permanent). The legacy 301/302 let clients downgrade a POST to a GET mid-redirect — which silently drops your request body. If a POST must survive a redirect, it's 307/308 or nothing.

---

## Response classes: when each

| Class | Use for |
|-------|---------|
| `JSONResponse` | The default — every `dict`/model you return becomes one |
| `Response` | Full control: raw bytes, custom `media_type` (XML, plain text) |
| `RedirectResponse` | Redirects — defaults to 307; pass `status_code=303` after form POSTs |
| `FileResponse` | A file on disk — streams it, sets `Content-Length` and type (lesson 03-2) |
| `StreamingResponse` | Content generated on the fly: large exports, server-sent events — nothing buffered in RAM |

```python
from fastapi.responses import RedirectResponse, StreamingResponse

@app.post("/form-submit")
async def form_submit():
    return RedirectResponse("/thanks", status_code=303)   # browser GETs /thanks; refresh is safe

@app.get("/export.csv")
async def export():
    async def rows():                                     # generator: one row in memory at a time
        yield "id,name\n"
        for i in range(1_000_000):
            yield f"{i},item-{i}\n"
    return StreamingResponse(rows(), media_type="text/csv")
```

---

## Recap & next

- ✅ Headers and cookies are declared params too — `Annotated[... , Header()/Cookie()]`, with automatic underscore↔hyphen mapping and free validation.
- ✅ Identifying cookies always get `httponly` + `samesite` + `secure` — each flag blocks a specific attack.
- ✅ `Request` is for raw material (bytes, IP, URL); declared params beat it for anything with a schema.
- ✅ GET/PUT/DELETE are retry-safe; POST is not — design POST endpoints knowing networks retry.
- ✅ 201 carries `Location`; 204 carries nothing; 303 after forms; 307/308 when the method must survive a redirect.
- ✅ Self-check: a client POSTs to an endpoint that returns 302, and the body vanishes on the redirected request. Why — and which status code fixes it?

→ Next: **[03-2 · Forms & file uploads](02_forms_and_file_uploads.md)**

## Exercises

1. Write `GET /headers-demo` that requires an `X-API-Version` header, returns 400 if it's missing, and echoes it back in a response header of the same name.

<details>
<summary>Solution</summary>

```python
@app.get("/headers-demo")
async def headers_demo(
    response: Response,
    x_api_version: Annotated[str | None, Header()] = None,
):
    if x_api_version is None:
        raise HTTPException(status_code=400, detail="X-API-Version header required")
    response.headers["X-API-Version"] = x_api_version
    return {"version": x_api_version}
```

The param is declared optional (`str | None`) because that's HTTP's reality — then *we* decide it's required and pick the status code, instead of letting a 422 leak validation internals for a missing header.
</details>

2. Build the post/redirect/get flow: `POST /guestbook` appends a name to an in-memory list and redirects; `GET /guestbook` shows the list. Verify with `curl -iL` that a refresh of the final page can't double-post.

<details>
<summary>Solution</summary>

```python
ENTRIES: list[str] = []

@app.post("/guestbook")
async def sign(name: Annotated[str, Form()]):
    ENTRIES.append(name)
    return RedirectResponse("/guestbook", status_code=303)  # 303 → client GETs

@app.get("/guestbook")
async def show():
    return {"entries": ENTRIES}
```

`curl -iL -F name=ada http://localhost:8000/guestbook` shows the 303, then the followed GET. The browser's address bar now points at a GET — refreshing re-reads, never re-signs. With 307 instead, the redirect would *re-POST* and duplicate the entry.
</details>

3. Explain in two sentences why `DELETE /files/{id}` returning 404 on the second call is a debatable design, given DELETE's idempotency promise.

<details>
<summary>Solution</summary>

Idempotency means the *state outcome* of repeating the call is identical — and it is: the file is gone either way, so both 204-then-404 and 204-then-204 are idempotent. The debate is about the *response*: returning 404 on the repeat tells retrying clients "your earlier delete may have worked, or the id never existed" — many teams return 204 both times so a retried DELETE never looks like an error.
</details>
