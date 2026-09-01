# 10-2 · Server API & SDK

> **Level:** Intermediate · **Prerequisites:** [10-1 · Local dev & Studio](01_local_dev_and_studio.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph-sdk 0.4.2; calls require a running server)

## Why this matters

Once your graph runs as a LangGraph Server (locally via `langgraph dev` or deployed), other programs talk to it over a **REST API** — no importing your graph code. The Server has a small, consistent object model, and the **SDK** wraps it in a typed client. Learn the three nouns — **assistants**, **threads**, **runs** — and you know the whole API.

---

## The object model

| Object | What it is |
|--------|-----------|
| **Assistant** | a graph + a config (a deployable "version" of your graph, e.g. different prompts/models) |
| **Thread** | a conversation — holds the checkpointed state history (your `thread_id`, now a first-class resource) |
| **Run** | one execution of an assistant on a thread (invoke or stream) |

The Server manages persistence (threads = checkpoints), so you don't attach a checkpointer yourself (10-1). Extras it provides: **streaming** runs, **background** runs, **cron** schedules, **webhooks**, and **double-texting** handling (what to do when a user sends a new message while a run is in flight).

---

## The Python SDK

`langgraph-sdk` (installed with the main package) gives you `get_client` (async) and `get_sync_client`:

```python
from langgraph_sdk import get_client

client = get_client(url="http://127.0.0.1:2024")   # your langgraph dev server

# 1. pick an assistant (by the graph name from langgraph.json)
assistants = await client.assistants.search()
assistant_id = assistants[0]["assistant_id"]

# 2. create a thread (a conversation)
thread = await client.threads.create()

# 3. stream a run on that thread
async for chunk in client.runs.stream(
    thread["thread_id"], assistant_id,
    input={"messages": [{"role": "user", "content": "hello"}]},
    stream_mode="updates",
):
    print(chunk.event, chunk.data)
```

The same `stream_mode`s from [02-2](../02_execution_model/02_streaming.md) work over the wire. A synchronous version is identical with `get_sync_client` and no `await`.

> **Note:** these calls need a server listening at `url`. With `langgraph dev` running (10-1), the snippet works as-is; without it you'll get a connection error. That's why this lesson shows code shapes rather than captured output — the rest of the course runs locally, but the Server is a service.

---

## Threads = persistence you don't manage

Because the Server owns threads, memory "just works": create a thread once, run against it repeatedly, and the conversation history persists server-side. Time-travel is API-level too — you can list a thread's checkpoints and fork from one, the hosted version of [05-2](../05_persistence_and_memory/02_time_travel.md).

```python
# list a thread's state history (checkpoints) over the API
history = await client.threads.get_history(thread["thread_id"])
```

---

## REST directly

No SDK required — it's plain HTTP. For example, creating a thread:

```bash
curl -X POST http://127.0.0.1:2024/threads -H "Content-Type: application/json" -d '{}'
```

The SDK is just an ergonomic wrapper; any language can call the endpoints.

---

## Recap & next

- ✅ Server model: **assistants** (graph+config), **threads** (conversations/checkpoints), **runs** (executions).
- ✅ `get_client`/`get_sync_client` from `langgraph-sdk` drive it; same `stream_mode`s as local.
- ✅ Threads mean server-managed persistence and API-level time-travel; plus cron/webhooks/background runs.
- ✅ Self-check: which Server object corresponds to your local `thread_id`?

→ Next: **[10-3 · Deployment options](03_deployment_options.md)**

## Exercises

1. With `langgraph dev` running (10-1), use the sync SDK to create a thread and stream one run against your chatbot assistant.

<details>
<summary>Solution</summary>

```python
from langgraph_sdk import get_sync_client
c = get_sync_client(url="http://127.0.0.1:2024")
aid = c.assistants.search()[0]["assistant_id"]
th = c.threads.create()
for ch in c.runs.stream(th["thread_id"], aid,
                        input={"messages": [{"role": "user", "content": "hi"}]},
                        stream_mode="updates"):
    print(ch.event, ch.data)
```
</details>
