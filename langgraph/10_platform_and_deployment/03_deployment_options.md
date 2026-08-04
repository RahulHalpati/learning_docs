# 10-3 · Deployment options

> **Level:** Intermediate · **Prerequisites:** [10-2 · Server API & SDK](02_server_api_and_sdk.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (concepts; deployment needs infra/accounts)

## Why this matters

There's no single "deploy" button — there's a spectrum from fully-managed to fully-DIY, and the right pick depends on how much ops you want to own. Knowing the three tiers stops you from either over-engineering a hobby project or under-provisioning a real one.

---

## The three tiers

| Tier | What | Best for | Trade-off |
|------|------|----------|-----------|
| **Managed (LangGraph Platform / Cloud)** | LangChain hosts the Server for you | teams wanting zero-ops | least control, a bill |
| **Self-hosted** | you run the Server (Docker) on your infra | compliance / data-residency needs | you own the ops |
| **DIY (FastAPI + graph)** | wrap the graph yourself in any framework | maximum flexibility, existing stack | you rebuild persistence/streaming/threads |

Tiers 1–2 give you everything from Section 10 (assistants, threads, cron, webhooks) for free. Tier 3 gives you *only* what you build.

---

## Managed / self-hosted (the Platform way)

Both run the same Server; the difference is *who* runs it. The build artifact comes from your `langgraph.json` (10-1). Self-hosting is typically:

```bash
langgraph build -t my-agent      # build a Docker image from langgraph.json
# then deploy that image (Cloud Run, GKE, ECS, your k8s) with a Postgres + Redis it needs
```

Managed hosting skips the infra: push your repo, LangChain builds and runs it, you get a URL and the SDK from 10-2 points at it. Choose self-hosted when data can't leave your environment; managed when you'd rather not run Postgres/Redis yourself.

---

## DIY with FastAPI

When you want the graph inside an existing service (and don't need assistants/threads/cron), wrap it yourself. You bring your own persistence (a checkpointer) and expose your own endpoints:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

DB = "postgresql://user:pass@localhost:5432/langgraph"

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(DB) as cp:
        await cp.setup()
        app.state.graph = build_my_graph(checkpointer=cp)   # your builder
        yield

app = FastAPI(lifespan=lifespan)

@app.post("/chat")
async def chat(user_id: str, message: str):
    cfg = {"configurable": {"thread_id": f"user-{user_id}"}}
    out = await app.state.graph.ainvoke(
        {"messages": [{"role": "user", "content": message}]}, cfg)
    return {"response": out["messages"][-1].content}
```

Here *you* own the checkpointer (unlike the Platform, which provides it). You also give up the Server's built-in streaming endpoints, thread management, and cron — reimplement only what you need.

> **Tip:** Start DIY only if you already run FastAPI and your needs are simple. The moment you want streaming endpoints, thread history, scheduled runs, or double-texting handling, the Platform has already built and tested them — don't reinvent that.

---

## Choosing

- **Prototype / learning:** run locally with `langgraph dev` (10-1).
- **Product, small team:** managed Platform.
- **Regulated / on-prem:** self-hosted Server.
- **Embed in an existing app, simple needs:** DIY FastAPI.

---

## Recap & next

- ✅ Managed → self-hosted → DIY is a spectrum of "how much ops do you own".
- ✅ Platform tiers give assistants/threads/cron/webhooks for free; DIY gives only what you build.
- ✅ `langgraph build` produces a Docker image; DIY FastAPI means you own the checkpointer.
- ✅ Self-check: which tier would you pick for an on-prem app that must keep all data in-house?

→ Next: **[99 · Capstone: Research Assistant](../99_project_research_assistant/README.md)**

## Exercises

1. Sketch (no need to deploy) which tier you'd choose for: (a) a weekend side project, (b) a healthcare app with data-residency rules, (c) a feature inside an existing FastAPI product.

<details>
<summary>Solution</summary>

(a) local `langgraph dev` then managed if it grows; (b) self-hosted Server for data residency; (c) DIY FastAPI wrapper if needs are simple, else self-hosted alongside the existing service.
</details>
