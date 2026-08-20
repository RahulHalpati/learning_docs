# Section 03 · Resources & prompts (and the Context object)

> **Prerequisites:** [02 · Your first MCP server](../02_first_server_fastmcp/README.md) · **Time:** ~4 h

Section 02 gave notevault **tools** — things the model can *do*. But a tool is the wrong shape for read-only data and for reusable workflows. This section adds the other two primitives: **Resources** (URI-addressed, read-only context the host loads on demand — the "GET" of MCP) and **Prompts** (parameterized, user-invoked templates your server ships so good workflows live in the server, not copy-pasted into every chat). It also introduces the **Context** object — the back-channel a running tool uses to log, report progress, and talk to the host mid-call.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 03-1 | [Resources](01_resources.md) | How do I expose read-only data the host can pull into context? |
| 03-2 | [Prompts](02_prompts.md) | How do I ship a reusable, parameterized workflow the user picks from a menu? |
| 03-3 | [Context & capabilities](03_context_and_capabilities.md) | How does a running tool talk back to the host — logs, progress, questions? |

## Mini-project

Extend **notevault** (still the in-memory store from Section 02) with resources, a prompt, and Context:

- A **templated resource** `note://{note_id}` that returns one note's content.
- A **static resource** `notes://recent` that lists the most recently created notes (metadata + their `note://` URIs).
- A **prompt** `summarize_notes(topic)` that guides the client to pull the relevant notes (via the resources and the `search_notes` tool from Section 02) and write a short summary.
- One **tool that uses Context** — e.g. `export_notes` — to `ctx.info(...)` what it's doing and `ctx.report_progress(...)` as it walks the store.

**Requirements checklist:**

- [ ] `note://{note_id}` returns content and raises a clear error for an unknown id.
- [ ] `notes://recent` returns JSON (a list of `{id, title, uri}`), newest first.
- [ ] Both resources are **read-only** — running them mutates nothing.
- [ ] `summarize_notes(topic)` is a real `@mcp.prompt` taking a `topic` parameter; it names the tools/resources the client should use.
- [ ] `export_notes` declares `ctx: Context` and emits at least one log line plus progress updates.
- [ ] The server starts and the primitives list via `uv run`.

## Test task (gate)

You're handed a server where two primitives are the wrong *kind*, plus an instruction string that should have been a prompt:

```python
# broken_server.py — three things are miscategorized. Fix all three.

@mcp.tool                                    # (A)
def read_note(note_id: str) -> str:
    return NOTES[note_id].body

@mcp.resource("notes://delete-all")          # (B)
def delete_all_notes() -> str:
    NOTES.clear()
    return "all notes deleted"

# (C) hardcoded instruction, pasted into client code by hand
INSTRUCTIONS = "Summarize the user's notes about a topic in 5 bullets."
```

**Fix all three, with written justification:**

1. **(A) `read_note` as a tool.** A pure, read-only lookup addressed by an id is a **resource**, not a tool. Convert it to `@mcp.resource("note://{note_id}")`. Justify: resources are read-only, URI-addressed context the *host* loads; making it a tool wrongly puts a plain lookup in the model's action budget.
2. **(B) `delete_all_notes` as a resource.** A resource **must be side-effect-free** — reading it must never change state. A destructive action is a **tool**, and a *dangerous* one, so it should be gated (Section 03-3 shows `ctx.elicit`). Convert it to `@mcp.tool`.
3. **(C) the `INSTRUCTIONS` string.** A reusable instruction is a **prompt**. Convert it to a parameterized `@mcp.prompt def summarize_notes(topic: str) -> str` so the workflow lives in the server and takes an argument.

**You pass when** all three are re-categorized correctly, you can *explain in one sentence each why* (read-only vs. side-effecting vs. reusable template), and your `summarize_notes` prompt actually takes a parameter and returns a template that references it.

## What you'll be able to do after this section

- Expose read-only data as **resources** — static (`notes://recent`) and templated (`note://{note_id}`) — with stable URIs and no hidden side effects.
- Ship reusable workflows as **prompts** the user invokes by name, and explain why that beats copy-pasting instructions.
- Pick the right primitive for a capability and defend it: read → resource, act → tool, reusable template → prompt.
- Use the **Context** object to log, report progress, and (at a glance) sample the host's model or ask the user a question mid-call.

→ Start: **[03-1 · Resources](01_resources.md)**
