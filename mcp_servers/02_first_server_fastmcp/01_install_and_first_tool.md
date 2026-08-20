# 02-1 · Install & your first tool

> **Level:** Beginner · **Prerequisites:** [01 · Foundations](../01_foundations/README.md)
> **Time:** ~40 min · **Verified:** 2026-08-08 (FastMCP · MCP Inspector · Python 3.12 · uv)

## Why this matters

In Section 01 you learned *what* a tool is: a model-controlled action, advertised with a name, a description, and an input schema. This lesson is where that stops being abstract — you'll write an ordinary Python function, decorate it, and FastMCP will generate the whole schema for you **from the function's type hints and docstring**. That auto-generation is the single most important idea in the section: the signature and docstring you write *are* the contract the model reads to decide whether and how to call your tool. Get comfortable with it here; we sharpen it into a craft in [02-3](03_tool_design_contract.md).

---

## Start the project

FastMCP is a normal Python package; we manage the project with **uv** (the same toolchain used across these courses). Create the project, pin Python, and add the dependency:

```bash
uv init notevault            # creates pyproject.toml + a starter file
cd notevault
uv python pin 3.12           # writes .python-version → requires-python ">=3.12"
uv add fastmcp               # adds fastmcp to pyproject and locks it
```

`uv add fastmcp` pulls in FastMCP and the MCP SDK it builds on, and records them in `pyproject.toml`. Delete the starter file uv created; we'll write `server.py` next. Everything from here runs through `uv run`, so the right virtualenv is always used — no manual `activate`.

---

## The FastMCP instance

A server is one `FastMCP` object. Everything you expose — tools, and later resources and prompts — hangs off it:

```python
# server.py
from fastmcp import FastMCP

# The name identifies your server to hosts (it shows up in the Inspector and
# in Claude Desktop's server list). One FastMCP instance = one server.
mcp = FastMCP("notevault")
```

That's the whole server object. It has no tools yet, so a host connecting to it would see an empty `tools/list`. Let's give it one.

---

## Your first tool

A tool is a function decorated with `@mcp.tool`. It works on **sync or async** functions — use `async def` when the body does I/O (a DB call, an HTTP request); a plain `def` is fine for pure logic. Our store is an in-memory dict for now, so sync is honest:

```python
# server.py (continued)
from uuid import uuid4
from pydantic import BaseModel

class Note(BaseModel):
    id: str
    title: str
    body: str
    tags: list[str]

# In-memory store for now. A real database arrives in Section 04.
NOTES: dict[str, Note] = {}

@mcp.tool
def create_note(title: str, body: str, tags: list[str] | None = None) -> Note:
    """Save a new note to the knowledge base and return the stored note.

    Use this whenever the user wants to remember, capture, or write down
    a piece of information for later retrieval.
    """
    note = Note(id=uuid4().hex[:8], title=title, body=body, tags=tags or [])
    NOTES[note.id] = note        # persist into the in-memory store
    return note                  # a typed return → structured output (see 02-3)
```

Three decisions worth naming:

- **Type hints are mandatory, not optional.** `title: str`, `tags: list[str] | None`, `-> Note` — FastMCP reads these to build the schema. An un-annotated parameter becomes an untyped, useless slot in the schema. (This is why the "no hints" version in the [Section gate](README.md#test-task-gate) fails.)
- **`tags: list[str] | None = None`** makes tags optional and, with the default, keeps the schema honest: the model sees `tags` is not required. We coalesce to `[]` inside, avoiding the mutable-default footgun.
- **`-> Note`** returns a typed Pydantic model. FastMCP turns that into *structured output* — the client gets a machine-readable object, not a blob of text it has to parse. More on why that matters in 02-3.

---

## What FastMCP generated

You wrote a function. The host sees a **JSON schema**. When a client calls `tools/list`, FastMCP hands back this (abridged) for `create_note`:

```json
{
  "name": "create_note",
  "description": "Save a new note to the knowledge base and return the stored note.\n\nUse this whenever the user wants to remember, capture, or write down\na piece of information for later retrieval.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "title": { "type": "string", "title": "Title" },
      "body":  { "type": "string", "title": "Body" },
      "tags":  {
        "anyOf": [{ "type": "array", "items": { "type": "string" } }, { "type": "null" }],
        "default": null, "title": "Tags"
      }
    },
    "required": ["title", "body"]
  }
}
```

Read it the way the model does. The **`description` is your docstring**. The **`inputSchema` is your signature**: parameter names, types, which are `required` (`title` and `body`; `tags` isn't, because it has a default). Because the return is a typed `Note`, FastMCP *also* emits an `outputSchema` describing `{id, title, body, tags}` — so the client knows the shape it will get back.

> **This is the contract.** The model never sees your Python. It sees exactly this JSON, and *only* this JSON, when deciding whether `create_note` fits the task and what to pass. Notice one gap already: the parameters have **no descriptions** yet — the model can see `title` is a required string, but nothing tells it *what* a title should be. That's the crack we fix with `Annotated[..., Field(description=...)]` in [02-3](03_tool_design_contract.md).

---

## Run it over stdio

Add the entry point and run the file:

```python
# server.py (end of file)
if __name__ == "__main__":
    mcp.run()        # no transport argument → defaults to stdio
```

```bash
uv run server.py
```

`mcp.run()` with no arguments starts the **stdio transport**: the server reads JSON-RPC requests from **stdin** and writes responses to **stdout**. This is exactly what a desktop host (Claude Desktop, an IDE) launches as a subprocess and pipes to.

> **"It just hangs!"** Correct — and that's success, not a bug. Over stdio the server is *waiting for JSON-RPC on stdin*. There's no prompt, no banner asking for input; it's a pipe, not a REPL. You don't drive a stdio server by typing into it — you point a **client** at it. That's the entire job of the next lesson: the MCP Inspector connects, lists your tool, and calls it. Press `Ctrl-C` to stop it for now.

---

## Recap & next

- ✅ A FastMCP server is one `mcp = FastMCP("name")` object; tools hang off it via `@mcp.tool`.
- ✅ `@mcp.tool` works on **sync or async** functions; use `async def` for real I/O.
- ✅ FastMCP builds the tool's JSON schema **from your type hints and docstring** — the `description` is the docstring, the `inputSchema` is the signature.
- ✅ A **typed return** (a Pydantic `Note`) becomes **structured output** with its own `outputSchema`.
- ✅ `mcp.run()` defaults to **stdio**; `uv run server.py` starts it, and it *waits* on stdin — you drive it with a client, not by typing.
- ✅ Self-check: your `create_note` schema shows `required: ["title", "body"]` but not `tags`. Which line in the signature made `tags` optional?

→ Next: **[02-2 · The Inspector & wiring a host](02_inspector_and_clients.md)**

## Exercises

1. Add a second tool `count_notes() -> int` that returns how many notes are stored. What does its `inputSchema` look like, and why?

<details>
<summary>Solution</summary>

```python
@mcp.tool
def count_notes() -> int:
    """Return the total number of notes currently stored."""
    return len(NOTES)
```

Its `inputSchema` is `{"type": "object", "properties": {}, "required": []}` — an object with **no properties**, because the function takes no parameters. The model can call it with an empty argument object. The `outputSchema` is just `{"type": "integer"}` from the `-> int`.
</details>

2. Remove the `-> Note` return annotation from `create_note` (leave everything else). What disappears from the generated schema, and why does that make the tool worse for a model?

<details>
<summary>Solution</summary>

The **`outputSchema` disappears** — with no return type, FastMCP can't describe the output, so the client only gets loosely-typed text content back. The model then has to *guess* the shape of what it received (does it have an `id`? a `tags` list?) instead of reading a schema. Typed returns are how the model gets machine-readable output; dropping the annotation throws that away.
</details>

3. Why does FastMCP need the type hints to be present? What would the schema for `def create_note(title, body)` (no hints at all) look like?

<details>
<summary>Solution</summary>

FastMCP has no other source of truth for a parameter's type — Python doesn't enforce or infer types at runtime, so the annotation *is* the type information. Without hints, each parameter falls back to an **untyped/`any`-shaped slot**: the model sees `title` and `body` exist but not that they're strings, can't validate what it sends, and gets no guidance. Un-annotated tools are the classic "the model can't use it" failure — the whole point of the Section gate.
</details>
