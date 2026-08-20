# 03-1 · Resources

> **Level:** Beginner→Intermediate · **Prerequisites:** [02 · Your first MCP server](../02_first_server_fastmcp/README.md)
> **Time:** ~40 min · **Verified:** 2026-08-08 (FastMCP · MCP spec 2026-07-28 · Python 3.12)

## Why this matters

Tools are how the model *acts*; resources are how the host *reads*. If you expose read-only data as a tool, you burn the model's attention on lookups that the host could have loaded silently — and you blur the line between "safe to read" and "does something." Resources keep that line sharp: a URI you can fetch, that never changes anything.

---

## The store (from Section 02)

Everything below reads from notevault's in-memory store. Treat this as already defined:

```python
# notevault/store.py  — in-memory for now; real backend arrives in Section 04
from dataclasses import dataclass, field
from datetime import UTC, datetime

@dataclass
class Note:
    id: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

NOTES: dict[str, Note] = {}   # id -> Note; the tools in Section 02 write here
```

---

## A resource is the GET of MCP

A **resource** is data addressed by a **URI** that the host can read. Three properties define it:

- **Read-only.** Fetching a resource must not change anything — no writes, no deletes, no sends. Same request, same day, same answer. This is the whole invariant.
- **URI-addressed.** `note://abc123`, `notes://recent`, `file:///etc/hosts`. The scheme is yours to design.
- **Application-controlled.** The *host app* decides when to pull a resource into the model's context — attach a file, load a record. Contrast with **tools** (model decides to call one) and **prompts** (the *user* picks one). Section 01 drew this control split; resources are the "app loads it" corner.

Think HTTP: a resource is a `GET`, a tool is closer to a `POST`. If a capability *does something*, it is not a resource — no matter how convenient the URI looks.

---

## A static resource

The simplest resource has a fixed URI and takes no parameters. `notes://recent` lists the newest notes as JSON:

```python
from fastmcp import FastMCP

mcp = FastMCP("notevault")

@mcp.resource("notes://recent")               # fixed URI, no template
async def recent_notes() -> list[dict[str, str]]:
    """The 10 most recently created notes (metadata only)."""
    latest = sorted(NOTES.values(), key=lambda n: n.created_at, reverse=True)[:10]
    # Returning a non-str (list/dict) → FastMCP serializes it as application/json.
    return [
        {"id": n.id, "title": n.title, "uri": f"note://{n.id}"}
        for n in latest
    ]
```

Return a `str` and FastMCP serves it as `text/plain`; return a `dict`/`list`/Pydantic model and it serves JSON. Override with `@mcp.resource("notes://recent", mime_type="application/json")` if you want to be explicit. Note each item hands back a `note://{id}` URI — the client can follow those to read the full note next.

---

## A templated resource: parameters from the URI

Put `{placeholders}` in the URI and FastMCP fills the matching function parameters from the requested URI. One template answers a whole family of URIs:

```python
@mcp.resource("note://{note_id}")             # {note_id} in the URI → note_id parameter
async def get_note(note_id: str) -> str:
    """Return one note's rendered content, addressed by its id."""
    note = NOTES.get(note_id)
    if note is None:
        # Raising surfaces as a proper MCP error to the client — don't return "not found" as data.
        raise ValueError(f"no note with id {note_id!r}")
    return f"# {note.title}\n\n{note.body}"
```

A client that reads `note://abc123` gets that note; `note://xyz789` gets another — one function, one stable URI shape. The parameter name in the template **must** match the function parameter. Multi-segment templates work too: `note://{note_id}/tags` → `def note_tags(note_id: str)`.

---

## async resources

Resource functions can be `async def` — and should be, the moment reading means real I/O (a DB row, an object-store fetch, an HTTP call). The examples above are `async` already so nothing changes when Section 04 swaps `NOTES` for a database: only the body does.

```python
@mcp.resource("note://{note_id}/related")
async def related_notes(note_id: str) -> list[dict[str, str]]:
    """Notes sharing a tag with this one — cheap now, a query later."""
    note = NOTES.get(note_id)
    if note is None:
        raise ValueError(f"no note with id {note_id!r}")
    tags = set(note.tags)
    return [
        {"id": n.id, "title": n.title, "uri": f"note://{n.id}"}
        for n in NOTES.values()
        if n.id != note_id and tags & set(n.tags)      # shares ≥1 tag
    ]
```

Because the host reads resources on its own schedule, a slow synchronous resource would block the event loop just like a slow tool — keep them `async` and awaited.

---

## Resource design

Two rules keep resources trustworthy:

- **Stable URIs.** A URI is a contract. Clients cache them, and prompts (next lesson) reference them by name. `note://{note_id}` should mean the same thing next release. Version the scheme (`note://v2/...`) rather than silently changing what a URI returns.
- **Never hide an action in a resource.** The read-only invariant is the security boundary: a host may fetch resources automatically, without asking the user. If reading `notes://delete-all` deleted notes, an innocent context-load would destroy data. Anything with a side effect is a **tool** (and if destructive, a *gated* one — Section 03-3). This is exactly the miscategorization the section's gate makes you fix.

---

## Recap & next

- ✅ A **resource** is read-only data addressed by a **URI** — the "GET" of MCP; **application-controlled** (the host loads it).
- ✅ `@mcp.resource("notes://recent")` = static; `@mcp.resource("note://{note_id}")` = templated, params filled from the URI.
- ✅ Return `str` → text, return `dict`/`list` → JSON. Raise on not-found so it surfaces as an MCP error.
- ✅ Resource functions can be `async` — keep them so, for the real-backend swap in Section 04.
- ✅ Keep URIs stable; **never** put a side effect behind a resource.
- ✅ Self-check: why is exposing "delete all notes" as a resource a security bug, not just a style nit?

→ Next: **[03-2 · Prompts](02_prompts.md)**

## Exercises

1. Add a templated resource `notes://tag/{tag}` returning every note carrying that tag, as JSON, newest first.

<details>
<summary>Solution</summary>

```python
@mcp.resource("notes://tag/{tag}")
async def notes_by_tag(tag: str) -> list[dict[str, str]]:
    """All notes carrying `tag`, newest first."""
    matched = [n for n in NOTES.values() if tag in n.tags]
    matched.sort(key=lambda n: n.created_at, reverse=True)
    return [{"id": n.id, "title": n.title, "uri": f"note://{n.id}"} for n in matched]
```

A read-only lookup keyed by one path segment — textbook templated resource. No mutation, stable URI shape.
</details>

2. A teammate proposes `note://{note_id}/touch` that returns the note *and* bumps a `last_read_at` timestamp so "recently viewed" works. Why is that URI wrong, and what's the fix?

<details>
<summary>Solution</summary>

Reading it writes `last_read_at` — a side effect — so it breaks the read-only invariant. A host that auto-loads context would silently rewrite timestamps. Split it: keep `note://{note_id}` purely read-only, and if you truly need view-tracking, make **`mark_note_read(note_id)` a tool** the model calls deliberately. Reads and writes never share a primitive.
</details>
