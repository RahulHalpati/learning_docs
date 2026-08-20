# 02-3 · Tool design is contract design

> **Level:** Beginner · **Prerequisites:** [02-2 · The Inspector & wiring a host](02_inspector_and_clients.md)
> **Time:** ~45 min · **Verified:** 2026-08-08 (FastMCP · MCP Inspector · Python 3.12 · uv)

## Why this matters

A tool that *works* when you call it in the Inspector can still be a tool the model never calls, or calls wrong. The difference is the **contract**: the docstring and signature are the *entire* interface the model reads to decide whether your tool fits the task and what to pass it. This is the craft of the whole course — not "does the code run" but "can a model, seeing only the schema, use this correctly." A vague contract doesn't throw an error; it silently degrades into the model skipping your tool or feeding it garbage. This lesson is the set of habits that make a tool self-explanatory to a model.

---

## The model reads the schema, not your code

Say it plainly, because everything follows from it: **the model never sees your Python.** It sees the generated schema — the `description`, the parameter names and types, the `required` list, the output shape. Every design rule below is really one rule wearing different hats: *make the schema say exactly what the tool does and expects.* When the model "ignores your tool" or "calls it with nonsense," the schema was ambiguous. You don't fix that with a better model; you fix it by writing a better contract.

---

## Good vs. bad, side by side

Here's the same capability written twice. Both run. Only one is usable by a model.

```python
# ❌ Bad — a black box to the model
@mcp.tool
def proc(a: str, b: str, t=None):
    ...
    return {"a": a, "b": b}          # untyped dict, no output schema
```

The schema this generates: no `description`, parameters `a`/`b`/`t` with no descriptions (and `t` untyped), no `outputSchema`. The model can't tell what `proc` does, whether it's the right tool, or what `a` should be. It guesses or skips.

```python
# ✅ Good — a self-describing contract
from typing import Annotated
from pydantic import Field

@mcp.tool
def create_note(
    title: Annotated[str, Field(description="Short human-readable title for the note, e.g. 'Q3 planning'.")],
    body: Annotated[str, Field(description="The full note text. Plain text or Markdown.")],
    tags: Annotated[
        list[str] | None,
        Field(description="Lowercase topic tags for filtering later, e.g. ['python', 'async'].")
    ] = None,
) -> Note:
    """Save a new note to the knowledge base and return the stored note.

    Use this when the user wants to remember or capture information for later
    retrieval. Returns the stored note, including its generated id.
    """
    note = Note(id=uuid4().hex[:8], title=title, body=body, tags=tags or [])
    NOTES[note.id] = note
    return note
```

The schema now carries a description for the tool *and every parameter*, plus a typed `Note` output. A model reading this knows what the tool is for, exactly what each field means (with examples), which are required, and what it gets back. That's the difference between a tool that gets used and one that gets ignored.

---

## Describe every parameter with `Annotated` + `Field`

Type hints tell the model a parameter is a `str`; they don't tell it *what string*. Is `query` a note id, a search term, a URL? Close that gap with `Annotated[T, Field(description=...)]` on **every** parameter:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def search_notes(
    query: Annotated[str, Field(
        description="Text to look for in note titles, bodies, and tags. Case-insensitive."
    )],
) -> list[Note]:
    """Search saved notes and return every note that matches the query.

    Matches when the query text appears in a note's title, body, or any tag.
    Returns an empty list when nothing matches — that is a normal result, not an error.
    """
    q = query.lower()
    return [
        n for n in NOTES.values()
        if q in n.title.lower() or q in n.body.lower() or any(q in t.lower() for t in n.tags)
    ]
```

Two habits worth stealing here: **put examples in descriptions** (`e.g. ['python', 'async']`) — models pattern-match on them — and **state the boundary cases in the docstring** ("an empty list is normal, not an error"), so the model doesn't treat "no results" as a failure to retry or apologize for.

---

## Return typed, structured output

A tool that returns a bare string forces the model to *parse prose*. A tool that returns a **Pydantic model** (or dataclass) hands the client a machine-readable object *and* an `outputSchema` describing it. FastMCP does this automatically from the return annotation:

```python
class Note(BaseModel):
    id: str
    title: str
    body: str
    tags: list[str]

# `-> Note` and `-> list[Note]` both yield structured output.
# The client receives {id, title, body, tags}, not a blob it has to interpret.
```

Structured output means the model can *chain* your tool: call `create_note`, read the returned `id`, and pass it straight to a later `get_note(id)`. With a string return, the `id` is buried in prose and the model has to extract it — fragile and error-prone. Type your returns; it's free structure.

---

## Errors are data the model reads

When something goes wrong, don't crash and don't return `{"error": "..."}` prose. **Raise** — FastMCP converts a raised exception into a *tool error* that's delivered to the client as data the model can read and act on. For user-facing, model-facing messages, use `ToolError`:

```python
from fastmcp.exceptions import ToolError

@mcp.tool
def get_note(note_id: Annotated[str, Field(description="The id returned by create_note.")]) -> Note:
    """Fetch one note by its id."""
    note = NOTES.get(note_id)
    if note is None:
        # A ToolError is a clean, user-facing message the model can read and
        # recover from — not a stack trace, and not a server crash.
        raise ToolError(f"No note found with id {note_id!r}.")
    return note
```

The distinction that matters: **a tool error is a result, not an outage.** The server keeps running; the model receives "no note with id 'abc123'" and can adjust — search first, or tell the user. A raised *generic* exception also becomes a tool error, but its message may be hidden for safety; `ToolError` messages are meant to be shown. Write them for the reader: say what went wrong and, when useful, what to do instead.

---

## One job per tool — avoid the "god tool"

The strongest temptation is to fold ten behaviors into one tool with ten optional parameters — a `manage_note(action, id?, title?, body?, tags?, query?, ...)` that does create, read, update, delete, and search depending on which arguments are set. Resist it:

```python
# ❌ God tool — the model must reason about which combination of 8 optional
#    params is valid for which hidden "action". Most combinations are nonsense.
@mcp.tool
def manage_note(action: str, id=None, title=None, body=None, tags=None, query=None): ...

# ✅ One clear job each — the model picks the right tool by name, and every
#    parameter is meaningful for that tool.
@mcp.tool
def create_note(...): ...
@mcp.tool
def get_note(...): ...
@mcp.tool
def search_notes(...): ...
```

A god tool pushes a branching decision onto the model ("which params does `action='update'` need?") that it will get wrong. Small, single-purpose tools with descriptive names are easier for the model to select *and* give it a clean schema per job. If you can't describe a tool in one sentence without "or," it's two tools.

---

## Recap & next

- ✅ The **docstring + signature are the tool's contract** — the only thing the model reads to decide whether and how to call it. Ambiguity there = the model skips or misuses the tool.
- ✅ Describe **every parameter** with `Annotated[T, Field(description=...)]`; put examples in the descriptions and boundary cases in the docstring.
- ✅ Return a **typed Pydantic model** for structured output — it gives the model machine-readable results it can chain, not prose to parse.
- ✅ **Raise `ToolError`** for user-facing failures; a tool error is *data the model reads*, not a crash.
- ✅ **One job per tool.** Avoid god tools with many optional params — split by name so each schema is clean.
- ✅ Self-check: a colleague's tool `run(x: str, mode: str)` is never called by the model. Name two schema-level fixes before touching the logic.

→ Next: **[03 · Resources & prompts](../03_resources_and_prompts/README.md)**

## Exercises

1. Rewrite this tool so a model can use it correctly. State what each change fixes in the schema.

```python
@mcp.tool
def find(x: str):
    return [n.title for n in NOTES.values() if x in n.body]
```

<details>
<summary>Solution</summary>

```python
@mcp.tool
def find_notes_by_body(
    text: Annotated[str, Field(description="Text to search for within note bodies. Case-insensitive.")],
) -> list[Note]:
    """Return every note whose body contains the given text.

    Returns an empty list when nothing matches — a normal result, not an error.
    """
    t = text.lower()
    return [n for n in NOTES.values() if t in n.body.lower()]
```

Fixes: a **descriptive name** (`find` → `find_notes_by_body`) and a **docstring** give the tool a `description`; **`Annotated[..., Field(description=...)]`** on `text` tells the model what to pass; **`-> list[Note]`** gives a structured `outputSchema` (titles-only strings lost the ids/tags the model might need next); and the docstring states the empty-list boundary case.
</details>

2. Why is raising `ToolError("note 'abc' not found")` better for the model than returning `{"ok": False, "error": "not found"}`?

<details>
<summary>Solution</summary>

`ToolError` is delivered to the client through the protocol's **error channel** — the model receives an unambiguous *tool error* and knows the call failed, so it can recover (search first, ask the user). A `{"ok": False, ...}` dict is a **successful result** as far as the protocol is concerned; the model has to notice the `ok` flag and interpret prose to realize it failed — a convention it may miss. Use the error channel for errors; don't smuggle failures into successful return values.
</details>

3. You're asked to add "update an existing note's body." Do you add a `body`/`id` param combo to `create_note`, or make a new tool? Defend it in contract terms.

<details>
<summary>Solution</summary>

Make a **new tool**, `update_note(note_id, body)`. Bolting update onto `create_note` turns a clean "create a note" contract into a conditional one — the model would have to infer that "pass an `id` to update, omit it to create," a hidden rule the schema can't express well and the model will get wrong. Two single-purpose tools each have an unambiguous schema and are selected by name. One job per tool keeps every contract clean.
</details>
