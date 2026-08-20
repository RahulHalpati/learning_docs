# 04-1 · Async DB & the lifespan pattern

> **Level:** Intermediate · **Prerequisites:** [03 · Resources & prompts](../03_resources_and_prompts/README.md)
> **Time:** ~40–50 min · **Verified:** 2026-08-08 (FastMCP · aiosqlite/asyncpg · httpx · Python 3.12)

## Why this matters

notevault's `dict` was fine for teaching primitives, but it dies with the process and can't survive two workers. Real tools read and write a real datastore — and the single biggest mistake when you make that jump is opening the connection *inside* the tool. Do that and every call leaks a connection until the server falls over. The fix is the same pattern your FastAPI course already taught: open the expensive things **once** in a **lifespan**, reuse them, close them on shutdown.

---

## Where we were: the in-memory store

Sections 02–03 kept notes in a process-local dict:

```python
# notevault/store.py  — in-memory; retired this lesson
NOTES: dict[str, Note] = {}   # gone the instant the server restarts
```

It has three fatal flaws for anything real: **no durability** (restart = data gone), **no sharing** (two worker processes = two different stores), and **no query engine** (every filter is a Python loop over the whole dict). A database fixes all three. Locally we'll use **SQLite via aiosqlite**; the exact same tool code runs against **Postgres via asyncpg** in production — only the connection setup changes.

---

## The schema and an async connection

SQLite gives us a real table with a real primary key. Note the graduation: Section 03's `id: str` becomes a DB-assigned **`INTEGER PRIMARY KEY`**.

```python
# notevault/db.py
import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

async def connect(path: str = "notevault.db") -> aiosqlite.Connection:
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row     # rows subscript like dicts: row["title"]
    await conn.executescript(SCHEMA)     # idempotent — CREATE IF NOT EXISTS
    await conn.commit()
    return conn
```

`aiosqlite` runs SQLite on a background thread and hands you an `async` API, so `await conn.execute(...)` never blocks the event loop. Everything below `await`s its I/O.

---

## The lifespan: open once, reuse, close on shutdown

You met this idea in FastAPI's `lifespan`: an async context manager that runs setup **before** the app serves traffic and teardown **after** it stops. FastMCP has the same hook — pass an async context manager when you construct the server. Whatever it `yield`s becomes shared state every tool can reach.

```python
# notevault/server.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import aiosqlite
import httpx
from fastmcp import FastMCP

from notevault.db import connect


@dataclass
class AppState:                # the shared, expensive things — created ONCE
    db: aiosqlite.Connection
    http: httpx.AsyncClient


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppState]:
    # --- startup: runs before the first request ---
    db = await connect("notevault.db")
    http = httpx.AsyncClient(timeout=10.0)   # one client, connection-pooled, reused
    try:
        yield AppState(db=db, http=http)     # <- exposed to every tool/resource
    finally:
        # --- shutdown: always runs, even on error ---
        await http.aclose()
        await db.close()


mcp = FastMCP("notevault", lifespan=lifespan)
```

This is *exactly* the FastAPI lifespan mental model — startup / `yield` / shutdown — just on an MCP server. One connection, one HTTP client, for the life of the process.

> **Note on the accessor.** FastMCP's lifespan/startup hook takes an async context manager and stores what it yields; you read it back through the Context (below). The precise import and accessor path can shift between FastMCP releases — pin your version and check `Context` in your installed build. The *pattern* (open once, reuse, close on shutdown) is what's stable and what matters.

---

## Reaching shared state from a tool

A tool declares `ctx: Context` (as in Section 03) and pulls the shared state out of the request's lifespan context. No `connect()` in sight:

```python
from fastmcp import Context
from fastmcp.exceptions import ToolError   # clean errors — full treatment in 04-2


@mcp.tool
async def get_note(note_id: int, ctx: Context) -> dict[str, str | int]:
    """Fetch one note by id."""
    state: AppState = ctx.request_context.lifespan_context   # the shared AppState
    async with state.db.execute(
        "SELECT id, title, body, created_at FROM notes WHERE id = ?", (note_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        raise ToolError(f"note {note_id} not found")   # actionable, not a traceback
    return dict(row)
```

Every tool shares the *same* `state.db` — no per-call connection, no leak. If reaching through `ctx.request_context.lifespan_context` feels verbose, a common alternative is to stash the state in a module-level holder set inside the lifespan; both are fine, pick one and stay consistent.

---

## Writes: parameterize, then commit

The same shared connection handles writes. Two non-negotiables: **use `?` placeholders** (never f-string SQL — that's an injection hole), and **commit**.

```python
@mcp.tool
async def create_note(title: str, body: str, ctx: Context) -> dict[str, str | int]:
    """Create a note and return it (with its new id)."""
    state: AppState = ctx.request_context.lifespan_context
    async with state.db.execute(
        "INSERT INTO notes (title, body) VALUES (?, ?) RETURNING id, created_at",
        (title, body),
    ) as cur:
        row = await cur.fetchone()
    await state.db.commit()                 # SQLite: single writer — keep writes short
    return {"id": row["id"], "title": title, "body": body, "created_at": row["created_at"]}
```

---

## Resources query the DB too

The `note://{note_id}` resource from Section 03 changes only its body — the URI contract stays identical. FastMCP coerces the URI segment to the parameter's type (`note_id: int` here):

```python
@mcp.resource("note://{note_id}")
async def note_resource(note_id: int, ctx: Context) -> str:
    """One note's rendered content, read straight from the DB."""
    state: AppState = ctx.request_context.lifespan_context
    async with state.db.execute(
        "SELECT title, body FROM notes WHERE id = ?", (note_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        raise ValueError(f"no note with id {note_id}")   # surfaces as an MCP error
    return f"# {row['title']}\n\n{row['body']}"
```

Because the host may load a resource on its own schedule, a *synchronous* DB call here would block the loop just like a slow tool — keep it `async` and awaited.

---

## The production swap: Postgres via asyncpg

SQLite is one file and one writer — perfect locally. In production you want a real **connection pool** against Postgres. Only the lifespan changes; tool bodies stay `async` and query-shaped:

```python
import asyncpg

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppState]:
    # asyncpg gives a REAL pool: min/max connections, handed out per query
    pool = await asyncpg.create_pool(dsn="postgresql://...", min_size=1, max_size=10)
    http = httpx.AsyncClient(timeout=10.0)
    try:
        yield AppState(db=pool, http=http)
    finally:
        await http.aclose()
        await pool.close()

# in a tool: acquire a connection from the pool for the query, then release it
async def get_note(note_id: int, ctx: Context) -> dict:
    pool = ctx.request_context.lifespan_context.db
    async with pool.acquire() as conn:                       # borrowed from the pool
        row = await conn.fetchrow("SELECT * FROM notes WHERE id = $1", note_id)
    ...
```

Note Postgres uses `$1` placeholders (not `?`) and `create_pool` gives you the thing SQLite doesn't need: many connections for many concurrent queries. The lifespan is still "open once, reuse, close" — the pool *is* the reused resource.

---

## Recap & next

- ✅ Retire the in-memory `dict`: no durability, no sharing, no query engine. Real tools query a real store.
- ✅ **Never** `connect()` inside a tool — that leaks a connection per call. Open it **once** in a **lifespan**.
- ✅ FastMCP's lifespan is the FastAPI one you know: **startup → `yield` → shutdown**; what it yields is shared state.
- ✅ Reach shared state via `ctx.request_context.lifespan_context` (or a module-level holder) — same connection everywhere.
- ✅ Parameterize SQL with `?` (`$1` on Postgres); `commit()` writes; keep everything `async` and awaited.
- ✅ Prod swap = SQLite → asyncpg **pool**; tool bodies barely change.
- ✅ Self-check: what specifically breaks when two worker processes each run `NOTES = {}` — and how does a shared DB fix it?

→ Next: **[04-2 · Robust tools: errors, limits & progress](02_robust_tools.md)**

## Exercises

1. Rewrite the leaky `search_notes` below so it uses the shared connection from the lifespan instead of opening its own. (Pagination comes in 04-2 — just fix the connection here.)

```python
@mcp.tool
async def search_notes(query: str) -> list[dict]:
    conn = await aiosqlite.connect("notevault.db")   # <- the leak
    async with conn.execute("SELECT * FROM notes WHERE body LIKE ?", (f"%{query}%",)) as cur:
        return [dict(r) for r in await cur.fetchall()]
```

<details>
<summary>Solution</summary>

```python
@mcp.tool
async def search_notes(query: str, ctx: Context) -> list[dict]:
    state: AppState = ctx.request_context.lifespan_context
    async with state.db.execute(
        "SELECT id, title, body FROM notes WHERE body LIKE ?", (f"%{query}%",)
    ) as cur:
        return [dict(r) for r in await cur.fetchall()]
```

Add `ctx: Context`, pull `state.db` from the lifespan context, and query *that*. The connection is created once at startup and reused — no per-call `connect()`, no leak.
</details>

2. Why open the `httpx.AsyncClient` in the lifespan instead of doing `httpx.get(url)` inside each tool?

<details>
<summary>Solution</summary>

A fresh client per call throws away connection pooling (a new TCP + TLS handshake every time — slow), and `httpx.get` is the *sync* API, which would block the event loop inside an `async` tool. One `AsyncClient` opened in the lifespan is pooled, reused, `await`able, and closed cleanly on shutdown — the same "open once, reuse, close" rule as the DB.
</details>
