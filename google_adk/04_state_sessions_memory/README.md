# Section 04 · State, sessions & memory

> **Prerequisites:** [02 · Agents & workflows](../02_agents_and_workflows/README.md) · **Time:** ~2 h

How ADK remembers. Sessions hold a conversation's **state** and events; the **memory service** carries knowledge across sessions; **artifacts** store binary outputs; **callbacks** let you observe and guard every step.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 04-1 | [Sessions & state](01_sessions_and_state.md) | How does session state work, and what do the `app:`/`user:`/`temp:` prefixes mean? |
| 04-2 | [Memory service](02_memory_service.md) | How do I remember facts across sessions and search them? |
| 04-3 | [Artifacts](03_artifacts.md) | How do I save and load binary outputs (files, images)? |
| 04-4 | [Callbacks](04_callbacks.md) | How do I hook before/after agent/model/tool for guardrails and logging? |

## What you'll be able to do after this section

- Read/write session state and understand state scopes/prefixes.
- Save finished sessions to memory and search them.
- Store and retrieve artifacts via the artifact service.
- Add before/after callbacks for logging, guardrails, and short-circuiting.

→ Start: **[04-1 · Sessions & state](01_sessions_and_state.md)**
