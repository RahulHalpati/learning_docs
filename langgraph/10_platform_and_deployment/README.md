# Section 10 · Platform & deployment

> **Prerequisites:** Sections [03](../03_building_graphs/README.md), [05](../05_persistence_and_memory/README.md) · **Time:** ~90 min

You've built graphs; now ship them. LangGraph's **Platform** turns a compiled graph into a running service with a REST API, persistence, a visual debugger (**Studio**), and client SDKs — plus a local dev server so you get all of that on your laptop first. This section covers local dev, the Server API + SDK, and deployment options.

> **Note:** unlike the rest of the course, these tools involve a running server (and, for cloud, an account), so outputs here are configs and commands rather than offline runs. Everything you learned still applies — the Platform just *hosts* the graphs you already know how to build.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 10-1 | [Local dev & Studio](01_local_dev_and_studio.md) | How do I run my graph as a live server locally with `langgraph dev` and `langgraph.json`? |
| 10-2 | [Server API & SDK](02_server_api_and_sdk.md) | What does the Server expose (assistants, threads, runs), and how do I call it from code? |
| 10-3 | [Deployment options](03_deployment_options.md) | Managed, self-hosted, or DIY FastAPI — which and how? |

## What you'll be able to do after this section

- Write a `langgraph.json` and run `langgraph dev`; open your graph in Studio.
- Understand the Server's assistants/threads/runs model and drive it with the Python SDK.
- Choose between LangGraph Platform (managed/self-hosted) and a DIY FastAPI wrapper.

→ Start: **[10-1 · Local dev & Studio](01_local_dev_and_studio.md)**
