# Section 04 · Control flow

> **Prerequisites:** [03 · Building graphs](../03_building_graphs/README.md) · **Time:** ~2 h

Edges are how a graph *decides*. This section covers the full toolkit: plain **conditional edges**, the **`Command`** object (route *and* update state in one move — the basis of agent handoffs), the **`Send`** API for dynamic map-reduce fan-out, and **subgraphs** for composing graphs inside graphs.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 04-1 | [Conditional edges](01_conditional_edges.md) | How do routing functions and path maps decide the next node? |
| 04-2 | [`Command` — route + update](02_command.md) | How does a node update state *and* choose where to go — and hand off across graphs? |
| 04-3 | [`Send` & map-reduce](03_send_map_reduce.md) | How do I fan out dynamic parallel work over a list and gather it? |
| 04-4 | [Subgraphs](04_subgraphs.md) | How do I nest a graph as a node, with the same or a different state schema? |

## What you'll be able to do after this section

- Write conditional edges with routers and path maps, including cycles.
- Return `Command(update=..., goto=...)` from a node; navigate to a parent graph for handoffs.
- Use `Send` to spawn N parallel node instances and reduce their results.
- Compose subgraphs both as compiled nodes and as state-transforming functions.

→ Start: **[04-1 · Conditional edges](01_conditional_edges.md)**
