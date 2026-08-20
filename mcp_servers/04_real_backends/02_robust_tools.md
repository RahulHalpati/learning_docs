# 04-2 · Robust tools: errors, limits & progress

> **Level:** Intermediate · **Prerequisites:** [04-1 · Async DB & the lifespan pattern](01_async_db_and_lifespan.md)
> **Time:** ~40–50 min · **Verified:** 2026-08-08 (FastMCP · aiosqlite/asyncpg · httpx · Python 3.12)

## Why this matters

A tool that works in a demo and a tool that survives production differ in the unglamorous parts: what happens when the id is wrong, when the URL hangs, when the query matches ten thousand rows. Get these wrong and you either crash, leak internals to the model, or quietly blow the context window. The three disciplines in this lesson — **clean errors**, **result-size limits**, and **progress** — are what make a tool safe for an autonomous model to call unattended.

---

## Errors: `ToolError`, never a traceback

When a tool hits a bad input or a missing record, it must tell the model *something actionable* — not dump a Python stack trace. FastMCP draws a sharp line: raise **`ToolError`** and its message is sent to the client verbatim; raise anything else and FastMCP masks it behind a generic "internal error" so your internals never leak.

```python
from fastmcp.exceptions import ToolError

@mcp.tool
async def get_note(note_id: int, ctx: Context) -> dict:
    state: AppState = ctx.request_context.lifespan_context
    async with state.db.execute(
        "SELECT id, title, body FROM notes WHERE id = ?", (note_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        # Actionable: says what's wrong AND how to recover.
        raise ToolError(f"No note with id={note_id}. Call search_notes to find valid ids.")
    return dict(row)
```

The distinction is deliberate. A `ToolError` is *for the model* — "that id doesn't exist, try searching." A raw `KeyError` traceback is *for you* — it leaks table names, file paths, and stack frames the model has no business seeing and might parrot back. Convert boundaries you don't control (a `KeyError`, a DB integrity error) into a `ToolError` with a clean message.

---

## Validate inputs at the boundary

The model fills in tool arguments — sometimes wrongly. Validate with `Annotated` + Pydantic `Field` so bad values are rejected *before* they reach your SQL, and so the constraints show up in the tool's schema for the model to read:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
async def search_notes(
    query: Annotated[str, Field(min_length=1, max_length=200)],
    limit: Annotated[int, Field(ge=1, le=100)] = 20,     # capped — see next block
    cursor: Annotated[int, Field(ge=0)] = 0,
    ctx: Context = None,
) -> "NotePage":
    ...
```

An empty query or `limit=999999` never reaches the database — Pydantic rejects it and the model gets a precise validation message. The bounds are documentation *and* enforcement in one place.

---

## Result-size discipline: the MCP-specific concern

This is the one that bites hardest and is easiest to miss. **A tool's return value is fed straight into the model's context window.** Return 5000 rows and you have:

- **A token bill on every call.** Those rows are serialized to text and counted as input tokens — expensive, and repeated every time the model re-reads the conversation.
- **A blown window.** A big enough result simply doesn't fit, and the call fails or truncates unpredictably.
- **No recourse for the model.** A human scrolls a UI; the model gets one blob it can't page. If you didn't give it a way to ask for "the next 20," it's stuck with whatever you dumped.

So **you** paginate, on the model's behalf: return a bounded page, the total count, and a cursor to fetch more.

```python
from pydantic import BaseModel

class Note(BaseModel):
    id: int
    title: str
    body: str

class NotePage(BaseModel):
    items: list[Note]
    total: int                    # how many match in all — context the model needs
    next_cursor: int | None       # pass this back for the next page; None = done

@mcp.tool
async def search_notes(
    query: Annotated[str, Field(min_length=1, max_length=200)],
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
    cursor: Annotated[int, Field(ge=0)] = 0,
    ctx: Context = None,
) -> NotePage:
    """Search notes by body text. Returns one page; follow next_cursor for more."""
    state: AppState = ctx.request_context.lifespan_context
    like = f"%{query}%"
    async with state.db.execute("SELECT COUNT(*) FROM notes WHERE body LIKE ?", (like,)) as cur:
        (total,) = await cur.fetchone()
    async with state.db.execute(
        "SELECT id, title, body FROM notes WHERE body LIKE ? ORDER BY id LIMIT ? OFFSET ?",
        (like, limit, cursor),
    ) as cur:
        rows = await cur.fetchall()
    next_cursor = cursor + limit if cursor + limit < total else None
    return NotePage(items=[Note(**dict(r)) for r in rows], total=total, next_cursor=next_cursor)
```

Now the model sees `total=4213`, gets 20 rows, and knows to call again with `cursor=20` if it needs more. It's in control, and the context stays small. **Treat result size as a correctness property of the tool, not a nicety** — the hard cap on `limit` is what makes it impossible for a naive model call to blow the window.

---

## Timeouts on external calls

An outbound HTTP call that hangs holds a slot open forever. Always set a timeout — belt (the client default from the lifespan) and braces (per-call when needed) — and turn failures into a `ToolError`:

```python
import httpx

@mcp.tool
async def enrich_note(
    note_id: int,
    url: Annotated[str, Field(pattern=r"^https?://")],
    ctx: Context,
) -> dict:
    """Fetch `url` and store a short excerpt on the note."""
    state: AppState = ctx.request_context.lifespan_context
    try:
        resp = await state.http.get(url, timeout=10.0)   # shared client, explicit timeout
        resp.raise_for_status()
    except httpx.TimeoutException:
        raise ToolError(f"Fetching {url} timed out after 10s.")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"{url} returned {e.response.status_code}.")
    excerpt = resp.text[:2000]
    await state.db.execute("UPDATE notes SET body = body || ? WHERE id = ?", (excerpt, note_id))
    await state.db.commit()
    return {"id": note_id, "added_chars": len(excerpt)}
```

Never leave a network call untimed inside a tool — one slow host shouldn't be able to pin a worker indefinitely.

---

## Progress on long-running tools

A bulk import might insert hundreds of rows. Use the `Context` back-channel (Section 03-3) to stream progress so the host can show a bar instead of a frozen spinner:

```python
class ImportResult(BaseModel):
    imported: int

@mcp.tool
async def import_notes(rows: list[Note], ctx: Context) -> ImportResult:
    """Bulk-insert notes, reporting progress as it goes."""
    state: AppState = ctx.request_context.lifespan_context
    total = len(rows)
    for i, note in enumerate(rows, start=1):
        await state.db.execute("INSERT INTO notes (title, body) VALUES (?, ?)", (note.title, note.body))
        await ctx.report_progress(progress=i, total=total)   # streams to the host
    await state.db.commit()
    await ctx.info(f"imported {total} notes")
    return ImportResult(imported=total)
```

Progress is *communication*, not just polish: a long tool that reports nothing looks hung, and a host (or user) may kill it.

---

## Idempotency for retryable actions

MCP calls get retried — by the host, by a flaky network, by a model that didn't see the first response. If `create_note` isn't idempotent, a retry silently creates a **duplicate**. Accept a client-supplied key and make the second call a no-op:

```python
# schema adds:  request_id TEXT UNIQUE
@mcp.tool
async def create_note(title: str, body: str, request_id: str, ctx: Context) -> Note:
    """Create a note. Safe to retry: same request_id returns the same note."""
    state: AppState = ctx.request_context.lifespan_context
    await state.db.execute(
        "INSERT INTO notes (title, body, request_id) VALUES (?, ?, ?) "
        "ON CONFLICT(request_id) DO NOTHING",     # retry with same id → no duplicate
        (title, body, request_id),
    )
    await state.db.commit()
    async with state.db.execute(
        "SELECT id, title, body FROM notes WHERE request_id = ?", (request_id,)
    ) as cur:
        return Note(**dict(await cur.fetchone()))
```

Read-only tools are naturally idempotent; the ones that need this are **writes and sends** — anything a retry could duplicate.

---

## Return structured types, not stringified blobs

Every tool above returns a Pydantic model or a typed dict, not a hand-formatted string. FastMCP turns a structured return into **structured content plus a JSON schema**, so the model receives typed, machine-readable data it can reliably pick fields out of — `page.next_cursor`, not a regex over prose. Reach for a `BaseModel` return whenever the result has shape.

---

## Recap & next

- ✅ Raise **`ToolError`** with an actionable message; everything else is masked — tracebacks never reach the model.
- ✅ **Validate** inputs at the boundary with `Annotated` + `Field`; bad args never hit your SQL.
- ✅ **Result-size discipline is MCP-specific:** results land in the context window, so cap `limit` and return `items` + `total` + `next_cursor`. The model can't page a blob you dumped — paginate *for* it.
- ✅ **Timeout** every external call; convert timeouts/HTTP errors into `ToolError`.
- ✅ Report **progress** on long tools via `ctx.report_progress`.
- ✅ Make retryable writes **idempotent** with a client `request_id`.
- ✅ Return **structured types** so the model gets typed data, not prose.
- ✅ Self-check: a teammate says "just return all matching notes, the model can handle it." Give the two-part reason (token cost + no paging) that this is wrong on an MCP tool specifically.

→ Next: **[04-3 · Composition & OpenAPI](03_composition_and_openapi.md)**

## Exercises

1. `list_all_notes()` returns every note in the table as one list. Rewrite it as a paginated tool.

<details>
<summary>Solution</summary>

```python
@mcp.tool
async def list_notes(
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
    cursor: Annotated[int, Field(ge=0)] = 0,
    ctx: Context = None,
) -> NotePage:
    state: AppState = ctx.request_context.lifespan_context
    async with state.db.execute("SELECT COUNT(*) FROM notes") as cur:
        (total,) = await cur.fetchone()
    async with state.db.execute(
        "SELECT id, title, body FROM notes ORDER BY id LIMIT ? OFFSET ?", (limit, cursor)
    ) as cur:
        rows = await cur.fetchall()
    next_cursor = cursor + limit if cursor + limit < total else None
    return NotePage(items=[Note(**dict(r)) for r in rows], total=total, next_cursor=next_cursor)
```

The bounded `limit` (`le=100`) is the load-bearing part — even a model that ignores pagination can't pull the whole table in one call.
</details>

2. This tool leaks internals. Fix it so the model gets a clean, actionable error and nothing else.

```python
@mcp.tool
async def delete_note(note_id: int, ctx: Context) -> str:
    state = ctx.request_context.lifespan_context
    del CACHE[note_id]          # KeyError if absent → traceback to the model
    return "deleted"
```

<details>
<summary>Solution</summary>

```python
@mcp.tool
async def delete_note(note_id: int, ctx: Context) -> dict:
    state: AppState = ctx.request_context.lifespan_context
    async with state.db.execute("DELETE FROM notes WHERE id = ? RETURNING id", (note_id,)) as cur:
        row = await cur.fetchone()
    await state.db.commit()
    if row is None:
        raise ToolError(f"note {note_id} not found — nothing deleted")
    return {"deleted": note_id}
```

`DELETE ... RETURNING` tells us whether a row actually existed. A miss becomes a `ToolError` the model can act on, not a raw `KeyError` dumping the stack. (In production, deletes should also be gated with human approval — Section 06.)
</details>
