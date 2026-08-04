# 08-1 · Containerize & Cloud Run

> **Level:** Intermediate · **Prerequisites:** [06-3 · API server & clients](../06_runtime_events_streaming/03_api_server_and_clients.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0; `adk deploy cloud_run` present, deploy needs GCP)

## Why this matters

The fastest way to get an ADK agent into production is **Cloud Run** — serverless containers that scale to zero. ADK's `adk deploy cloud_run` builds the container and deploys it in one command, so you don't hand-write a Dockerfile or a server.

---

## One-command deploy

Given an agent package with a `root_agent` (the layout from [06-3](../06_runtime_events_streaming/03_api_server_and_clients.md)):

```bash
adk deploy cloud_run \
  --project=my-gcp-project \
  --region=us-central1 \
  path/to/agent_dir
```

ADK packages the agent (the same one `adk api_server` serves), builds a container, and deploys it to Cloud Run — you get an HTTPS URL running the REST API from 06-3. Scales to zero when idle, up under load.

---

## What you provide

- **A model the deployed agent can reach.** Cloud Run won't see your local Ollama — use Gemini/Vertex (or a hosted LiteLLM provider) in production, configured via env vars.
- **Persistence, if you need it.** For durable sessions/memory across instances, point the deployed agent at a database-backed `SessionService`/`MemoryService` rather than the in-memory ones.
- **Secrets** via Cloud Run env vars / Secret Manager — never in the image.

> **Note:** `adk deploy cloud_run` is verified present in `google-adk 2.5.0`; running it needs a GCP project and billing. The *artifact* is a normal container, so you can also `docker build` it yourself and deploy anywhere that runs containers.

---

## DIY container

If you'd rather own the Dockerfile (to add sidecars, custom middleware), wrap `adk api_server` (or a `Runner`) in your own image. You lose the one-command convenience but gain full control — the same managed-vs-DIY trade-off as [LangGraph's deployment tiers](../../langgraph/10_platform_and_deployment/03_deployment_options.md).

---

## Recap & next

- ✅ `adk deploy cloud_run --project ... --region ... <agent_dir>` builds and deploys in one command.
- ✅ Production needs a reachable model (Gemini/Vertex/hosted), durable services, and Secret Manager.
- ✅ The artifact is a plain container — deploy it anywhere if you prefer DIY.
- ✅ Self-check: why can't the deployed agent use your local Ollama model?

→ Next: **[08-2 · GKE & Agent Engine](02_gke_and_agent_engine.md)**

## Exercises

1. Write the `adk deploy cloud_run` command for a `research/` agent in project `demo-proj`, region `europe-west1`.

<details>
<summary>Solution</summary>

`adk deploy cloud_run --project=demo-proj --region=europe-west1 research` — plus setting the agent's model to a cloud-reachable one via env vars before deploying.
</details>
