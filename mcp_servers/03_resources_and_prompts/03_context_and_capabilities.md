# 03-3 · Context & capabilities

> **Level:** Beginner→Intermediate · **Prerequisites:** [03-2 · Prompts](02_prompts.md)
> **Time:** ~40 min · **Verified:** 2026-08-08 (FastMCP · MCP spec 2026-07-28 · Python 3.12)

## Why this matters

A tool call shouldn't be a black box that goes quiet for thirty seconds and then either returns or throws. **Context** is the back-channel: while your function runs, it can log to the client, report progress on a long job, ask the host's model to generate something, or ask the *user* a question. Without it you can't tell "working" from "hung," and a destructive tool can't stop to confirm.

---

## Declaring `ctx: Context`

Add a parameter typed `Context` to any tool, resource, or prompt function. FastMCP sees the type and **injects** it per call — it is *not* a client-supplied argument and never appears in the primitive's public schema:

```python
from fastmcp import Context, FastMCP

mcp = FastMCP("notevault")

@mcp.tool
async def rebuild_index(ctx: Context) -> str:
    """Rebuild notevault's search index; report as it goes."""
    await ctx.debug("starting index rebuild")           # dev detail
    count = len(NOTES)
    await ctx.info(f"indexing {count} notes")           # client-visible log
    if count == 0:
        await ctx.warning("no notes to index")          # something notable, not fatal
    # ... build the index ...
    return f"indexed {count} notes"
```

`ctx.debug / info / warning / error` send **structured log messages back to the client** as the call runs — the host can show them in a status area or a log pane. This is your observability seam: a good tool narrates what it's doing so a human (or the model) can follow along. The functions are `async`, so `await` them.

---

## Progress on long tools

For anything that loops over real work, `ctx.report_progress(progress, total)` drives the host's progress bar so a long call reads as *moving*, not *frozen*:

```python
@mcp.tool
async def export_notes(ctx: Context) -> str:
    """Export every note to one markdown bundle, reporting progress."""
    notes = list(NOTES.values())
    total = len(notes)
    await ctx.info(f"exporting {total} notes")
    chunks: list[str] = []
    for i, note in enumerate(notes, start=1):
        chunks.append(f"# {note.title}\n\n{note.body}\n")
        await ctx.report_progress(progress=i, total=total)   # 1/total … total/total
    await ctx.info("export complete")
    return "\n---\n".join(chunks)
```

Report progress against a known `total` when you have one (the host shows a percentage); pass just `progress` for open-ended work. This is the tool from the mini-project — logging plus progress in one place.

---

## Sampling: the server asks the host's model

Sometimes your tool needs the LLM itself — to draft a title, classify text, condense a note. Rather than embed and pay for your own model, **sampling** asks the *host's* model to generate, via `ctx.sample(...)`:

```python
@mcp.tool
async def suggest_title(note_id: str, ctx: Context) -> str:
    """Ask the host's model to propose a title for a note."""
    note = NOTES[note_id]
    reply = await ctx.sample(f"Suggest a short, specific title for:\n\n{note.body}")
    return reply.text
```

The server borrows the client's model, so there's no separate API key or bill on your side — and the host stays in control, able to approve or deny the request. Reach for it when a tool's job genuinely needs generation; most tools don't.

---

## Elicitation: the server asks the user

**Elicitation** lets a running tool pause and ask the *user* for input — a confirmation, a missing field — then continue. It's the right gate for a destructive action like "delete all notes":

```python
@mcp.tool
async def delete_all_notes(ctx: Context) -> str:
    """Delete every note — asks the user to confirm first."""
    count = len(NOTES)
    # response_type=None → a plain confirm; the result carries an .action, no data.
    answer = await ctx.elicit(f"Delete all {count} notes? This cannot be undone.", response_type=None)
    if answer.action != "accept":                        # "decline" or "cancel"
        return "cancelled — nothing deleted"
    NOTES.clear()
    return f"deleted {count} notes"
```

This mid-call round-trip is possible because of the **2026 MRTR / stateless design** from [Section 01](../01_foundations/README.md): a call can suspend, hand a request back to the host, and resume on the reply, without the server holding a long-lived session. Elicitation is how a tool stays interactive — asking instead of guessing, or confirming instead of destroying.

---

## Why server → host callbacks matter

Tools, resources, and prompts flow *host → server*. Context flows the other way, **server → host**, mid-call — and that direction is what makes a server more than a request/response function:

- **Observability** — logs (`ctx.info/warning/error`) let humans and the model see *why* a tool did what it did.
- **Long jobs** — progress (`ctx.report_progress`) keeps slow work legible instead of looking hung.
- **Interactivity** — sampling and elicitation let a tool pull in the model or the user *while it runs*, so it can adapt instead of failing on the first unknown.

Context is how your server talks back during a call. Use it, and even a one-shot tool becomes a transparent, interruptible, adaptive step.

---

## Recap & next

- ✅ Declare `ctx: Context`; FastMCP **injects** it — it's not a client argument and isn't in the schema.
- ✅ `ctx.debug/info/warning/error` = structured **logs** to the client (observability).
- ✅ `ctx.report_progress(progress, total)` = a moving **progress bar** for long tools.
- ✅ `ctx.sample(...)` borrows the **host's model**; `ctx.elicit(...)` asks the **user** — both mid-call.
- ✅ Elicitation/sampling ride the **stateless MRTR** design: a call can suspend and resume without a sticky session.
- ✅ Self-check: which Context call would you add to make "delete all notes" safe, and why?

→ Next: **[04 · Real backends](../04_real_backends/README.md)**

## Exercises

1. Add progress + logging to `search_notes` so it reports how many notes it has scanned.

<details>
<summary>Solution</summary>

```python
@mcp.tool
async def search_notes(query: str, ctx: Context) -> list[dict[str, str]]:
    """Substring search across note bodies, with progress."""
    notes = list(NOTES.values())
    total = len(notes)
    await ctx.info(f"searching {total} notes for {query!r}")
    hits: list[dict[str, str]] = []
    for i, note in enumerate(notes, start=1):
        if query.lower() in note.body.lower():
            hits.append({"id": note.id, "title": note.title, "uri": f"note://{note.id}"})
        await ctx.report_progress(progress=i, total=total)
    await ctx.info(f"found {len(hits)} matches")
    return hits
```
</details>

2. Why is `ctx.sample` preferable to your MCP server calling an LLM API directly with its own key?

<details>
<summary>Solution</summary>

`ctx.sample` borrows the *host's* model, so there's no second API key, no separate bill, and no model config drift on the server side — and the host stays in control, able to approve, deny, or route the request. Calling an LLM API directly makes the server a paying LLM client with its own credentials to secure and its own model choices to keep in sync. Let the host own the model; the server just asks.
</details>
