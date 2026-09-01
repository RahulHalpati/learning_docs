# 10-1 · Local dev & Studio

> **Level:** Intermediate · **Prerequisites:** [03-1 · Your first chatbot](../03_building_graphs/01_first_chatbot.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9; CLI/Studio require a running server)

## Why this matters

Before you deploy, you want your graph running as a *server* you can poke at — with a visual view of state flowing through nodes, the ability to edit state mid-run, and time-travel in a UI. The **LangGraph CLI** (`langgraph dev`) plus **Studio** give you exactly that, locally, from a small config file.

---

## Install the CLI

```bash
uv pip install "langgraph-cli[inmem]"     # [inmem] = local in-memory server, no Docker/Postgres
```

This is a separate package from the `langgraph` library you've used — it's the tooling that *runs* your graphs as a service.

---

## `langgraph.json` — the project manifest

A LangGraph app is declared by a `langgraph.json` at the project root. It tells the server which graphs to expose and where they live:

```json
{
  "dependencies": ["."],
  "graphs": {
    "chatbot": "./app/graph.py:app"
  },
  "env": ".env"
}
```

- **`graphs`** maps a *name* → `path/to/file.py:variable`, where the variable is your compiled graph (or a factory function returning one).
- **`dependencies`** lists what to install (`"."` = this project).
- **`env`** points at a dotenv file for secrets.

So a module like `app/graph.py` just needs to expose a compiled graph named `app`:

```python
# app/graph.py
from langgraph.graph import StateGraph, START, END, MessagesState
# ... build builder ...
app = builder.compile()          # ← this is what langgraph.json references
```

> **Tip:** Don't pass a `checkpointer` when compiling a graph for the Platform — the Server provides its own persistence. Compiling with your own checkpointer there raises an error. Locally-run graphs (the rest of this course) *do* need one.

---

## Run it

```bash
langgraph dev
```

This starts a local server (default `http://127.0.0.1:2024`) with hot-reload, and prints a link that opens your graph in **LangGraph Studio** in the browser.

---

## What Studio gives you

Studio is a visual debugger for graphs:

- **See the graph** — your nodes and edges rendered live.
- **Run interactively** — submit input, watch state flow node by node.
- **Inspect state** at every step (the `get_state_history` view, visualized).
- **Edit & fork** — change state at a checkpoint and re-run from there (the `update_state` time-travel from [05-2](../05_persistence_and_memory/02_time_travel.md), with a UI).
- **Manage threads** — inspect and replay past conversations.

It's the same primitives you've used in code (streaming, checkpoints, time-travel, HITL) with a UI wrapped around them — invaluable when a multi-agent graph misbehaves and you want to *see* where.

---

## Recap & next

- ✅ `uv pip install "langgraph-cli[inmem]"`, declare graphs in `langgraph.json`, run `langgraph dev`.
- ✅ `graphs` maps names to `file.py:compiled_graph`; **don't** attach your own checkpointer for the Platform.
- ✅ Studio visualizes the graph and gives UI-driven streaming, state inspection, time-travel, and thread management.
- ✅ Self-check: why do you omit the checkpointer when compiling a graph for `langgraph dev`?

→ Next: **[10-2 · Server API & SDK](02_server_api_and_sdk.md)**

## Exercises

1. Write a `langgraph.json` for the chatbot from [03-1](../03_building_graphs/01_first_chatbot.md) (moving the graph into `app/graph.py` and exposing `app`), then run `langgraph dev`.

<details>
<summary>Solution</summary>

Put the builder + `app = builder.compile()` (no checkpointer) in `app/graph.py`, add the `langgraph.json` above with `"chatbot": "./app/graph.py:app"`, `uv pip install "langgraph-cli[inmem]"`, and run `langgraph dev`. The printed URL opens Studio.
</details>
