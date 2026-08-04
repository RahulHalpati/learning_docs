# Section 08 · Real-world use cases

> **Prerequisites:** Sections [03](../03_building_graphs/README.md)–[07](../07_multi_agent/README.md) · **Time:** ~90 min

Three end-to-end graphs that combine everything so far — routing, tools, loops, HITL, memory — into shapes you'll actually ship. Each is offline-verified and deterministic so you can run it and get the same output shown here.

## Modules

| # | Module | Key pattern |
|---|--------|-------------|
| 08-1 | [Support routing](01_support_routing.md) | intent classification → branch → escalate to a human |
| 08-2 | [Self-correcting RAG](02_self_correcting_rag.md) | retrieve → generate → evaluate → loop until good |
| 08-3 | [DevOps pipeline](03_devops_pipeline.md) | severity branch → auto-fix or human-approve → ticket |

## What you'll be able to do after this section

- Route a request by intent and escalate the hard cases to a person.
- Add a self-evaluation loop that re-tries until an answer is good enough.
- Gate irreversible operations behind a human approval, then record the outcome.

→ Start: **[08-1 · Support routing](01_support_routing.md)**
