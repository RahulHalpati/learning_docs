# 08-3 · The A2A protocol

> **Level:** Intermediate · **Prerequisites:** [05-1 · Delegation & transfer](../05_multi_agent_systems/01_delegation_and_transfer.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (google-adk 2.5.0, a2a-sdk 1.1.1; imports verified, live calls need running servers)

## Why this matters

Delegation and transfer ([Section 05](../05_multi_agent_systems/README.md)) work *inside one program*. But agents increasingly live in different services, teams, even frameworks. **A2A (Agent-to-Agent)** is an open protocol — backed by Google — for one agent to call another over the network, regardless of how each is built. It's how an **ADK agent can call a LangGraph agent** (and vice versa).

---

## Install the extra

```bash
pip install a2a-sdk        # ADK's A2A support builds on this
```

Two directions: **expose** your agent as an A2A server, and **consume** a remote A2A agent.

---

## Expose an ADK agent over A2A

`to_a2a` wraps an ADK agent as an A2A-compliant server app (an ASGI app you serve with uvicorn):

```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a       # verified import (needs a2a-sdk)
from google.adk.agents import LlmAgent

writer = LlmAgent(name="writer", model=..., instruction="Write concise reports.")

a2a_app = to_a2a(writer)     # an ASGI app exposing `writer` via the A2A protocol
# serve it:  uvicorn module:a2a_app --port 9000
```

Now *any* A2A client — another ADK agent, a LangGraph agent, a third-party one — can call `writer` over HTTP using the standard protocol, discovering its capabilities via an **agent card**.

---

## Consume a remote agent

`RemoteA2aAgent` turns a remote A2A endpoint into a local agent you can drop into `sub_agents` — so a remote agent participates in delegation exactly like a local one:

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent    # verified import

remote_writer = RemoteA2aAgent(
    name="writer",
    agent_card="http://localhost:9000/.well-known/agent-card.json",
)

coordinator = LlmAgent(name="coordinator", model=...,
                       instruction="Delegate writing to the writer.",
                       sub_agents=[remote_writer])     # a REMOTE agent as a sub-agent
```

From the coordinator's view, `remote_writer` is just another specialist — but it's running in a different process (or a different framework). Transfer/delegation works across the network transparently.

> **Note:** the `to_a2a` and `RemoteA2aAgent` imports are verified with `google-adk 2.5.0` + `a2a-sdk 1.1.1`; a live demo needs the server process running (serve `a2a_app` on `:9000`, then run the coordinator). The protocol is HTTP + JSON with an agent card for discovery — no shared code between the two sides.

---

## The cross-framework bridge

Because A2A is a *protocol*, not an ADK feature, a LangGraph agent wrapped as an A2A server can be a `RemoteA2aAgent` sub-agent here — and an ADK agent exposed via `to_a2a` can be called from a LangGraph app. That's the concrete answer to "can my ADK and LangGraph agents work together?": **yes, over A2A**. The two courses' capstones are both single-framework, but either could expose its writer over A2A for the other to consume.

---

## Recap & next

- ✅ A2A is an open protocol for agents to call each other over the network, across frameworks.
- ✅ `to_a2a(agent)` exposes an ADK agent as an A2A server; `RemoteA2aAgent(agent_card=...)` consumes a remote one.
- ✅ A `RemoteA2aAgent` drops into `sub_agents` — remote delegation looks local.
- ✅ Self-check: what makes A2A able to bridge an ADK agent and a LangGraph agent?

→ Next: **[99 · Capstone](../99_project_adk_research_assistant/README.md)**

## Exercises

1. Sketch a two-process demo: process A serves `writer` via `to_a2a` on `:9000`; process B has a coordinator with a `RemoteA2aAgent` pointing at it.

<details>
<summary>Solution</summary>

A: `a2a_app = to_a2a(writer)`, `uvicorn a:a2a_app --port 9000`. B: `RemoteA2aAgent(name="writer", agent_card="http://localhost:9000/.well-known/agent-card.json")` in a coordinator's `sub_agents`. Run A, then B — B delegates to A over A2A.
</details>
