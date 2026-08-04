# Section 07 · Multi-agent

> **Prerequisites:** [04-2 · Command](../04_control_flow/02_command.md) · [04-3 · Send](../04_control_flow/03_send_map_reduce.md) · [04-4 · Subgraphs](../04_control_flow/04_subgraphs.md) · **Time:** ~2 h

One agent with fifteen tools becomes an unfocused mess. The fix is **multiple specialized agents** that collaborate. This section builds the four canonical topologies with real, offline-verified code: **supervisor** (a router delegates), **swarm** (peers hand off), **hierarchical** (teams of teams), and **map-reduce** (parallel agents over a list).

## Modules

| # | Module | Topology |
|---|--------|----------|
| 07-1 | [Supervisor](01_supervisor.md) | one coordinator routes to workers, who report back |
| 07-2 | [Swarm & handoffs](02_swarm_and_handoffs.md) | peer agents pass control to each other via `Command` |
| 07-3 | [Hierarchical](03_hierarchical.md) | a top-level graph of team subgraphs |
| 07-4 | [Map-reduce agents](04_map_reduce_agents.md) | fan out one agent over many items with `Send`, then synthesize |

## What you'll be able to do after this section

- Build a supervisor that delegates and loops until done.
- Implement handoffs between peer agents with `Command(goto=...)`.
- Compose teams as subgraphs under a top-level coordinator.
- Parallelize an agent across a list and reduce the results.

> **Prebuilt shortcuts:** `langgraph-supervisor` and `langgraph-swarm` are separate packages that generate these topologies for you. This section builds them from primitives so you understand what those libraries produce — and can customize when they don't fit.

→ Start: **[07-1 · Supervisor](01_supervisor.md)**
