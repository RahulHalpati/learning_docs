# 03-2 · Prompts

> **Level:** Beginner→Intermediate · **Prerequisites:** [03-1 · Resources](01_resources.md)
> **Time:** ~40 min · **Verified:** 2026-08-08 (FastMCP · MCP spec 2026-07-28 · Python 3.12)

## Why this matters

The best workflows aren't code — they're *instructions*: "pull these notes, read each one, summarize in five bullets." If that lives as a string pasted into every user's chat, it drifts, rots, and can't take parameters. A **prompt** ships that workflow *from the server*, versioned and parameterized, so the user just picks it by name. It's how you package multi-step know-how once and hand it to every client.

---

## A prompt is a user-invoked template

A **prompt** is a named, parameterized template your server exposes. Its defining traits:

- **User-controlled.** Unlike a tool (model decides) or a resource (host loads), a *person* picks a prompt — from a slash-command menu, a "/" list, a button. Section 01's control split: prompts are the user's corner.
- **Server-authored & reusable.** You write it once, in the server. Every client gets the same, current version.
- **Parameterized.** Callers fill in arguments (`topic`, `language`, `tone`) that get baked into the returned template.
- **Not a tool.** A prompt returns *text for the model to act on*; it doesn't execute anything itself. It can *instruct* the model to call your tools and read your resources — but it never calls them for you.

The simplest prompt returns a string. FastMCP turns that string into a single user message:

```python
from fastmcp import FastMCP

mcp = FastMCP("notevault")

@mcp.prompt                                   # @mcp.prompt() also works
def explain_note(note_id: str) -> str:
    """Ask the model to explain a note in plain language."""
    return f"Read the resource note://{note_id} and explain it to me like I'm new to the topic."
```

The docstring becomes the prompt's description — what the user sees in the menu — so write it for them.

---

## `summarize_notes(topic)`: orchestrating tools + resources

The payoff: a prompt can choreograph the primitives you built. `summarize_notes` tells the model exactly which resources to read and which tool to call, then what to produce:

```python
from typing import Annotated
from pydantic import Field

@mcp.prompt
def summarize_notes(
    topic: Annotated[str, Field(description="What subject to summarize notes about")],
) -> str:
    """Pull the notes relevant to a topic and summarize them."""
    # NOTE: `{{id}}` is an escaped brace — it renders as the literal `{id}`,
    # not an f-string substitution. We want the model to see `note://{id}`.
    return (
        f"Summarize what notevault knows about '{topic}'.\n\n"
        f"1. Call the `search_notes` tool with query='{topic}' to find candidates, "
        f"and check the `notes://recent` resource for anything new.\n"
        f"2. Read each hit's full text via its `note://{{id}}` resource.\n"
        f"3. Write a tight 5-bullet summary of what they say about '{topic}', "
        f"citing each note's title. If nothing is relevant, say so plainly."
    )
```

The user picks *"summarize_notes"*, types a topic, and the server hands the model a complete, current playbook — one that already knows notevault's tool and resource names. Change the workflow (add a step, rename a tool) and every client gets the fix on the next call. No user edits their copy-pasted prompt, because there are no copies.

---

## Returning a message list

A string is one user message. For a few-shot or role-setup prompt, return a **list of messages** — FastMCP's `Message` helper builds them (`role` defaults to `"user"`):

```python
from fastmcp.prompts.prompt import Message

@mcp.prompt
def summarize_as(topic: str, persona: str) -> list[Message]:
    """Summarize a topic's notes in a chosen persona's voice."""
    return [
        Message(f"You are {persona}. Summarize concisely, in character.", role="assistant"),
        Message(f"Summarize notevault's notes about '{topic}' — read them via the "
                f"note://{{id}} resources first."),   # defaults to role="user"
    ]
```

Reach for the list form only when you genuinely need multiple turns or a preset assistant stance; a single string covers most prompts.

---

## Prompts vs. tools vs. system prompts

Three things that all "tell the model what to do" — different owners, different jobs:

| | Who invokes it | What it is | notevault example |
|---|---|---|---|
| **Prompt** | The **user** (picks from a menu) | A reusable, parameterized *template* the server ships | `summarize_notes(topic)` |
| **Tool** | The **model** (decides mid-task) | An *action* with effects the server executes | `search_notes`, `export_notes` |
| **System prompt** | The **host app** (baked into the session) | Global instructions for the whole conversation | "You help manage a notes vault." |

A prompt beats a pasted instruction on three axes: it **takes parameters**, it's **versioned in one place** (the server), and it's **discoverable** — the host lists it so users find it instead of reinventing it. A system prompt is host-wide and static; a prompt is a targeted, on-demand workflow the user reaches for.

---

## How the host surfaces prompts

The host lists your server's prompts (over `prompts/list`) and shows them to the user — commonly as slash-commands or a "/" picker (`/summarize_notes`), with each argument as a fill-in field and the docstring as the hint. When the user picks one, the host calls `prompts/get` with their arguments, gets back the rendered messages, and drops them into the conversation. You author the workflow; the host handles the menu and the plumbing.

---

## Recap & next

- ✅ A **prompt** is a **user-invoked**, server-authored, **parameterized** template — the user's corner of the control split.
- ✅ `@mcp.prompt` on a function; return a **string** (one user message) or a **`list[Message]`** (multi-turn).
- ✅ A prompt can **orchestrate** your tools + resources by naming them in its instructions — but it never calls them itself.
- ✅ Prompts beat pasted instructions: parameterized, versioned server-side, discoverable in the host menu.
- ✅ The docstring is the user-facing description; the host surfaces prompts as slash-commands / a picker.
- ✅ Self-check: why does shipping `summarize_notes` as a prompt age better than a text snippet in each user's chat?

→ Next: **[03-3 · Context & capabilities](03_context_and_capabilities.md)**

## Exercises

1. Write a prompt `weekly_review(tag)` that guides the model to gather this week's notes for a tag and produce a review with "Done", "Open questions", and "Next" sections.

<details>
<summary>Solution</summary>

```python
@mcp.prompt
def weekly_review(tag: str) -> str:
    """Turn this week's notes for a tag into a structured review."""
    return (
        f"Build a weekly review for the '{tag}' tag.\n"
        f"1. Read the `notes://tag/{tag}` resource and keep notes from the last 7 days.\n"
        f"2. Read each via its `note://{{id}}` resource.\n"
        f"3. Output three sections — **Done**, **Open questions**, **Next** — "
        f"as bullets, citing note titles."
    )
```

Parameterized, references stable resource URIs, and defines the output shape — the workflow lives in the server, not the user's memory.
</details>

2. A teammate makes `summarize_notes` a **tool** so "the model can call it automatically." What breaks, conceptually?

<details>
<summary>Solution</summary>

A prompt is *user-controlled* — the person chooses to run the summary workflow. As a tool it becomes *model-controlled*: the model might fire it unprompted, and a tool is supposed to *do* something, not hand back an instruction template. You'd also lose the host's prompt menu (discoverability) and the clean "user picked this" intent. The summary workflow is a template the user invokes → it's a prompt.
</details>
