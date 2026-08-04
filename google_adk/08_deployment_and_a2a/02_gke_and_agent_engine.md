# 08-2 · GKE & Agent Engine

> **Level:** Intermediate · **Prerequisites:** [08-1 · Containerize & Cloud Run](01_containerize_and_cloud_run.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (google-adk 2.5.0; `adk deploy gke`/`agent_engine` present, deploy needs GCP)

## Why this matters

Cloud Run is the easy default, but ADK offers two more Google Cloud targets for different needs: **GKE** (Kubernetes) when you want full control of the runtime, and **Vertex AI Agent Engine** — a *fully managed* agent runtime that handles sessions, memory, and scaling for you. Knowing the three lets you match the target to the job.

---

## The three targets

| Target | Command | What it is | Best for |
|--------|---------|-----------|----------|
| **Cloud Run** | `adk deploy cloud_run` | serverless containers, scale-to-zero | most apps; low ops (08-1) |
| **GKE** | `adk deploy gke` | your Kubernetes cluster | full control, existing k8s, special infra |
| **Agent Engine** | `adk deploy agent_engine` | Vertex's managed agent runtime | least ops; native sessions/memory/tracing |

All three are `adk deploy` subcommands (verified present in `google-adk 2.5.0`).

---

## GKE

```bash
adk deploy gke --project=my-proj --region=us-central1 --cluster_name=my-cluster path/to/agent_dir
```

ADK builds the container and applies Kubernetes manifests to your cluster. Choose GKE when you already run k8s, need custom networking/sidecars/GPUs, or have strict infra requirements. You own the cluster ops.

---

## Vertex AI Agent Engine

```bash
adk deploy agent_engine --project=my-proj --region=us-central1 path/to/agent_dir
```

Agent Engine is the **managed** runtime: it runs the agent, provides durable sessions and the **Memory Bank** ([04-2](../04_state_sessions_memory/02_memory_service.md)), scales automatically, and integrates Cloud tracing. It's the "least ops" option — the ADK counterpart to LangGraph's managed Platform.

---

## Choosing

- **Cloud Run** — default; serverless, cheap, low ops.
- **Agent Engine** — you want managed sessions/memory and zero infra to run.
- **GKE** — you need Kubernetes-level control or already live there.

For learning and small products, Cloud Run or Agent Engine. GKE is for teams with existing k8s and specific needs.

---

## Recap & next

- ✅ Three targets: Cloud Run (serverless), GKE (your k8s), Agent Engine (managed, native sessions/memory).
- ✅ Each is an `adk deploy` subcommand.
- ✅ Pick by ops appetite: Agent Engine (least) → Cloud Run → GKE (most control).
- ✅ Self-check: which target gives you managed sessions and Memory Bank without running infra?

→ Next: **[08-3 · A2A protocol](03_a2a_protocol.md)**

## Exercises

1. Match each to a target: (a) a hobby demo, (b) an app needing managed memory + auto-scaling, (c) a team standardized on GKE.

<details>
<summary>Solution</summary>

(a) Cloud Run (scale-to-zero, cheap); (b) Agent Engine (managed sessions/Memory Bank); (c) GKE (`adk deploy gke` into their cluster).
</details>
