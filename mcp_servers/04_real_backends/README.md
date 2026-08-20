# Section 04 · Tools over real systems: databases, APIs & composition

> **Prerequisites:** [03 · Resources & prompts](../03_resources_and_prompts/README.md) · **Time:** ~5 h

Until now notevault has been a toy: a Python `dict` that evaporates the moment the process restarts. This section makes it real. You'll wire tools and resources to live **async I/O** — an aiosqlite database opened once through a **lifespan** and reused across every call, an `httpx` client for outbound requests — then learn the discipline that separates a demo tool from a production one (typed errors, timeouts, and result-size limits), and finish by assembling several small servers into one with **server composition**.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 04-1 | [Async DB & the lifespan pattern](01_async_db_and_lifespan.md) | How do all my tools share one DB connection and one httpx client without leaking them? |
| 04-2 | [Robust tools: errors, limits & progress](02_robust_tools.md) | How do I fail cleanly, cap result size, and report progress on long calls? |
| 04-3 | [Composition & OpenAPI](03_composition_and_openapi.md) | How do I assemble a big server from modules — or expose a FastAPI app I already built? |

## Mini-project

Back **notevault** with a real async SQLite database. Retire the in-memory `dict` from Sections 02–03 and move every tool and resource onto a shared aiosqlite connection opened in a lifespan.

Build these:

- A **lifespan** async context manager that opens the aiosqlite connection **and** one `httpx.AsyncClient` on startup, and closes both on shutdown.
- `get_note`, `create_note`, and `search_notes` **tools** plus a `note://{note_id}` **resource**, all querying the shared connection — no per-call `connect()`.
- **Error handling:** a missing id or bad input raises a **`ToolError`** with a message the model can act on — never a leaked traceback.
- **Pagination** on `search_notes`: it returns a *page* (`items`, `total`, `next_cursor`), never the whole table.
- A **bulk `import_notes`** tool that reports **progress** via `Context` as it inserts.
- An **`enrich_note`** tool that fetches an external URL with the shared `httpx` client (with a timeout) and stores an excerpt/summary on the note.

**Requirements checklist:**

- [ ] A lifespan opens the aiosqlite connection + one `httpx.AsyncClient` once, and closes both on shutdown.
- [ ] Tools/resources reach the shared connection through the Context (or a module-level holder) — **no `aiosqlite.connect()` inside a tool body**.
- [ ] Not-found and validation failures raise `ToolError`; no stack trace ever reaches the model.
- [ ] `search_notes` returns `items` + `total` + `next_cursor` and enforces a max `limit` — it cannot return the whole table.
- [ ] `import_notes` calls `ctx.report_progress(...)` as it inserts.
- [ ] `enrich_note` uses the shared `httpx.AsyncClient` with an explicit timeout; a slow/failed fetch becomes a `ToolError`, not a hang.
- [ ] Runs under `uv run`, full type hints, `async` throughout.

## Test task (gate)

A robustness bug-hunt. You're handed a working-but-dangerous server. Every tool *functions* in a demo and *fails* under load. Diagnose each bug, then fix it.

```python
# leaky_server.py — four production bugs. Find and fix all four.
import requests                                  # (3)
from fastmcp import FastMCP

mcp = FastMCP("notevault")

@mcp.tool
async def search_notes(query: str) -> list[dict]:
    conn = await aiosqlite.connect("notevault.db")   # (1) new connection every call
    async with conn.execute(
        "SELECT * FROM notes WHERE body LIKE ?", (f"%{query}%",)
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]                # (2) could be 5000 rows

@mcp.tool
async def enrich_note(note_id: int, url: str) -> str:
    body = requests.get(url).text                # (3) sync call blocks the event loop
    return body[:2000]

@mcp.tool
async def get_note(note_id: int) -> dict:
    return CACHE[note_id]                         # (4) KeyError → traceback to the model
```

**Diagnose and fix, with a one-line reason each:**

1. **Connection leak.** `search_notes` calls `aiosqlite.connect()` on every invocation and never closes it → the process bleeds file handles / connections until it dies. **Fix:** open the connection once in a **lifespan** and reuse it from the Context (04-1).
2. **Context blow-up.** `search_notes` can return thousands of rows in one response. **Fix:** **paginate** — accept a bounded `limit` and a `cursor`, return `items` + `total` + `next_cursor` (04-2).
3. **Blocked event loop.** `requests.get` is synchronous; inside an `async` tool it freezes the whole server for every concurrent call. **Fix:** the shared **`httpx.AsyncClient`** with an explicit **timeout**, awaited (04-1, 04-2).
4. **Leaked traceback.** An unknown id raises a raw `KeyError`, dumping internals to the model. **Fix:** catch it and raise a clean **`ToolError`** (`f"note {note_id} not found"`) (04-2).

**You pass when** all four are fixed **and** you write a short note explaining *why returning huge results is uniquely bad for an MCP tool* — namely: a tool's result is fed straight into the **model's context window**, so 5000 rows costs real tokens (and money) on every call, and — unlike a human scrolling a UI — **the model can't page** a giant blob it's already been handed. You paginate *for* it: a bounded page plus a `next_cursor` the model can follow.

## What you'll be able to do after this section

- Move a server off an in-memory store onto real async I/O — an aiosqlite DB and an `httpx` client — opened once in a **lifespan** and reused everywhere.
- Access shared, expensive resources from any tool or resource without reconnecting per call, and swap SQLite for Postgres/asyncpg for production.
- Write tools that fail *cleanly* — typed `ToolError` messages the model can act on, never tracebacks — with input validation and timeouts on external calls.
- Apply **result-size discipline**: pagination, limits, and cursors, and explain why oversized results are a first-class MCP problem, not a nicety.
- Report progress on long-running tools, and make retryable actions idempotent.
- **Compose** a large server from small sub-servers, and generate an MCP server directly from a FastAPI app or OpenAPI spec — with the curation that auto-generation still demands.

→ Start: **[04-1 · Async DB & the lifespan pattern](01_async_db_and_lifespan.md)**
