# Section 01 · Foundations

> **Prerequisites:** [00 · Introduction](../00_introduction.md) · **Time:** ~90 min

Every LangGraph application — from a toy to a production multi-agent system — is built from four primitives: **State**, **Nodes**, **Edges**, and **Reducers**. This section teaches all four, then zooms in on the single most common state shape (messages) and gets your environment pinned and verified.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 01-1 | [Core concepts](01_core_concepts.md) | What are state, nodes, edges, and reducers — and how do they fit together? |
| 01-2 | [State & messages](02_state_and_messages.md) | How do I model conversation state with `MessagesState` and `add_messages`? What about `MessageGraph`? |
| 01-3 | [Environment setup](03_environment_setup.md) | How do I pin versions and run everything offline, no API key? |

## What you'll be able to do after this section

- Define typed graph state with `TypedDict` (and know when to use Pydantic).
- Write nodes that return partial updates, and wire fixed & conditional edges.
- Choose the right **reducer** so list fields accumulate instead of being overwritten.
- Model chat state with `MessagesState` / `add_messages`, and edit or delete messages by id.
- Run every sample **offline** with a deterministic fake model.

→ Start: **[01-1 · Core concepts](01_core_concepts.md)**
