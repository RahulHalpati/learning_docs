# Section 02 · Your first MCP server with FastMCP

> **Prerequisites:** [01 · Foundations](../01_foundations/README.md) · **Time:** ~4 h

Foundations gave you the mental model; now you build the thing. This section stands up your first real MCP server with **FastMCP** — the batteries-included Python framework where a plain, type-hinted function *becomes* a tool — running over **stdio**, the transport every desktop host speaks. You'll drive it by hand in the **MCP Inspector** before any model is involved, because the fastest way to ship a tool an LLM can actually use is to debug its *contract* without the LLM in the loop.

## Lessons

| # | Lesson | The question it answers |
|---|--------|-------------------------|
| 02-1 | [Install & your first tool](01_install_and_first_tool.md) | How do I turn a Python function into an MCP tool and run it? |
| 02-2 | [The Inspector & wiring a host](02_inspector_and_clients.md) | How do I *see* the generated schema, test calls, and plug into Claude Desktop? |
| 02-3 | [Tool design is contract design](03_tool_design_contract.md) | Why does the model skip my tool — and how do I write one it can't misuse? |

## Mini-project

Build **notevault v0** — a FastMCP server over a personal notes store. Storage is a plain in-memory `dict` (a real database arrives in Section 04); the point is to exercise the whole loop — function → schema → stdio → Inspector — in one small, honest server.

**Requirements checklist:**

- [ ] A `uv` project (`requires-python = ">=3.12"`) with `fastmcp` added, and a single `server.py` that creates `mcp = FastMCP("notevault")`.
- [ ] An in-memory store `NOTES: dict[str, Note]` keyed by note id, where `Note` is a Pydantic model (`id`, `title`, `body`, `tags`).
- [ ] `create_note(title, body, tags)` — a `@mcp.tool` that stores a new note and **returns the typed `Note`** (structured output). Every parameter is `Annotated[T, Field(description=...)]`, and the function has a one-job docstring.
- [ ] `search_notes(query)` — a `@mcp.tool` returning `list[Note]` for notes whose title, body, or tags contain `query` (case-insensitive). Its docstring states that an empty list is a normal result, not an error.
- [ ] `if __name__ == "__main__": mcp.run()` — the server runs over **stdio** via `uv run server.py`.
- [ ] **Verified in the MCP Inspector:** both tools listed; each schema shows *your* parameter descriptions and the structured `Note` output; you called `create_note` twice and `search_notes` once, by hand, and search found the right note.

## Test task (gate)

**"The model can't use your tool."** You're handed a server whose one tool is a black box to any LLM client. Your job is to make the model able to call it correctly, and to *explain why the original fails*.

```python
# leaky_tool.py — a tool the model keeps ignoring (or misusing). Fix it.
from fastmcp import FastMCP

mcp = FastMCP("scratch")

notes: dict[str, str] = {}

@mcp.tool
def save(a: str, b: str):
    notes[a] = b
    return {"a": a, "b": b, "ok": True}

if __name__ == "__main__":
    mcp.run()
```

Three deliverables:

1. **Explain the failure.** In writing, say *why a real LLM client would fail to call this or call it wrong.* The model never sees your source — it sees the generated schema. Here that schema has **no tool description** (no docstring), **meaningless parameter names** (`a`, `b`) with **no descriptions**, and **no output schema** (an untyped `dict` return). So the model can't tell what `save` does, what `a` and `b` should hold (is `a` a key? a title? a filename?), or what it gets back. It will skip the tool, or guess the arguments and mis-store data.
2. **Fix it.** Give the tool a clear name and one-line docstring; make every parameter `Annotated[str, Field(description="...")]` with a real name and description; return a **typed Pydantic model** so the output is structured and machine-readable. (It's a note store — so `save` becomes something like `create_note(title, body)` returning a `Note`.)
3. **Prove it in the Inspector.** Capture the tool's generated schema **before** and **after**. Before: no `description`, params `a`/`b` with no `description`, no `outputSchema`. After: a tool `description`, named params each carrying a `description`, and an `outputSchema` for the `Note`.

**You pass when** you can show the **before/after schema side by side** *and* write two or three sentences explaining that **the docstring and type hints are the tool's contract with the model** — the only thing the model reads to decide *whether* and *how* to call it. If the schema is vague, the model is guessing.

## What you'll be able to do after this section

- Scaffold a `uv` project, add **FastMCP**, and turn a type-hinted function into an MCP tool with `@mcp.tool`.
- Explain how FastMCP builds a tool's JSON schema from its **type hints and docstring** — and why that schema *is* the interface the LLM reads.
- Run a server over **stdio** and drive it by hand in the **MCP Inspector**, reading schemas and calling tools with no model involved.
- Wire a stdio server into a host (Claude Desktop's `mcpServers` config) and run the change → reload → re-test debugging loop.
- Design a tool the model can't misuse: descriptive `Annotated` params, one job per tool, typed/structured returns, and meaningful `ToolError` messages.

→ Start: **[02-1 · Install & your first tool](01_install_and_first_tool.md)**
