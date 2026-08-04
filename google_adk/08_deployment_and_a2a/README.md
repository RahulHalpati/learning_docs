# Section 08 · Deployment & A2A

> **Prerequisites:** [06 · Runtime, events & streaming](../06_runtime_events_streaming/README.md) · **Time:** ~90 min

Get your agent off your laptop, and let agents talk to each other. This section covers containerizing and deploying to Google Cloud (Cloud Run, GKE, Agent Engine) and the **A2A** protocol for cross-agent — even cross-framework — communication.

> **Note:** deployment targets need a Google Cloud account; A2A needs the `a2a-sdk` extra and a running server. These lessons show the commands and code (all verified to *exist* in the pinned versions) rather than live cloud runs.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 08-1 | [Containerize & Cloud Run](01_containerize_and_cloud_run.md) | How do I package and deploy an agent to Cloud Run? |
| 08-2 | [GKE & Agent Engine](02_gke_and_agent_engine.md) | What are the GKE and Vertex Agent Engine options? |
| 08-3 | [A2A protocol](03_a2a_protocol.md) | How do agents call each other — even across frameworks? |

## What you'll be able to do after this section

- Deploy an ADK agent with `adk deploy cloud_run` (and know the GKE/Agent Engine paths).
- Choose a deployment target by ops/scale needs.
- Expose an agent over **A2A** with `to_a2a`, and consume a remote one with `RemoteA2aAgent`.

→ Start: **[08-1 · Containerize & Cloud Run](01_containerize_and_cloud_run.md)**
