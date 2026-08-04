# Section 05 · Multi-agent systems

> **Prerequisites:** [02 · Agents & workflows](../02_agents_and_workflows/README.md) · **Time:** ~90 min

Real agents are teams. This section covers how ADK agents **delegate** and **transfer** control to specialists, the **coordinator** patterns that organize them, and how to mix deterministic workflow agents with LLM-driven routing.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 05-1 | [Delegation & transfer](01_delegation_and_transfer.md) | How does a coordinator hand a request to the right specialist? |
| 05-2 | [Coordinator patterns](02_coordinator_patterns.md) | How do I organize many agents (dispatcher, hierarchy)? |
| 05-3 | [Combining workflow & LLM agents](03_combining_workflow_and_llm.md) | How do I mix deterministic pipelines with LLM decisions? |

## What you'll be able to do after this section

- Wire `sub_agents` and understand automatic `transfer_to_agent` delegation.
- Build coordinator/dispatcher and hierarchical team structures.
- Combine `Sequential`/`Parallel`/`Loop` with LLM routing in one system.

→ Start: **[05-1 · Delegation & transfer](01_delegation_and_transfer.md)**
