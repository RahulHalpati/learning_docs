# 03-2 · Memory & Streaming

> **Level:** Beginner · **Prerequisites:** [03-1 Wiring & revision loop](01_wiring_and_revision_loop.md)
> **Time:** 20 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## Memory: why the graph remembers

By default, `graph.invoke()` starts fresh each time. Add a **checkpointer** and a
`thread_id` to persist state across multiple invocations:

```python
from langgraph.checkpoint.memory import MemorySaver

graph = builder.compile(checkpointer=MemorySaver())

# First call — starts fresh for thread "job-42"
result1 = graph.invoke(
    {"job_text": "Need a FastAPI backend", "revisions": 0, "max_revisions": 2},
    config={"configurable": {"thread_id": "job-42"}}
)

# Second call — same thread_id, resumes from saved state
result2 = graph.invoke(
    {"job_text": "Need a FastAPI backend", "revisions": 0, "max_revisions": 2},
    config={"configurable": {"thread_id": "job-42"}}
)
```

For the proposal agent, `MemorySaver` (in-process RAM) is enough. For production use
a persistent checkpointer like `SqliteSaver` or `PostgresSaver` from `langgraph-checkpoint-*`.

### thread_id = job session

Each unique `thread_id` is an independent conversation thread. In `generate_proposal()`:

```python
def generate_proposal(job_text: str, *, max_revisions: int = 2, thread_id: str = "default", **kwargs) -> dict:
    graph = build_graph(**kwargs)
    return graph.invoke(
        {"job_text": job_text, "revisions": 0, "max_revisions": max_revisions},
        config={"configurable": {"thread_id": thread_id}},
    )
```

Pass a unique `thread_id` per job (e.g. a UUID) when running multiple jobs concurrently.

---

## Streaming: watch agents run in real time

Instead of waiting for the whole graph to finish, `.stream()` yields updates after
each node. Use it to show a progress indicator or stream partial results to a UI.

```python
from proposal_agent.graph import build_graph
from langchain_core.language_models import GenericFakeChatModel

llm = GenericFakeChatModel(messages=iter([
    "analysis", "HIGH fit", "draft", "APPROVED"
]))
graph = build_graph(llm=llm)

for event in graph.stream(
    {"job_text": "Need a backend", "revisions": 0, "max_revisions": 2},
    config={"configurable": {"thread_id": "stream-demo"}},
):
    node_name = list(event.keys())[0]
    print(f"✓ {node_name} done")
```

Output (offline fake model):

```
✓ analyzer done
✓ matcher done
✓ writer done
✓ reviewer done
```

### Streaming in the CLI

Add progress output to the CLI with minimal changes:

```python
for event in graph.stream(initial_state, config=config):
    node = list(event.keys())[0]
    print(f"  [{node}] ✓", flush=True)
print()  # blank line before the proposal
```

---

## Streaming in the Streamlit UI

The Streamlit app (`app_streamlit.py`) calls `generate_proposal()` (which uses
`invoke`, not `stream`) but shows a spinner. For a per-node progress bar, swap in
`graph.stream()` and update `st.status()`:

```python
import streamlit as st
from proposal_agent.graph import build_graph

graph = build_graph()
with st.status("Agents running…") as status:
    for event in graph.stream(initial_state, config=config):
        node = list(event.keys())[0]
        status.update(label=f"✓ {node} completed")
```

---

## Recap

| Feature | How |
|---|---|
| Persist state across calls | `MemorySaver()` checkpointer + `thread_id` |
| One job, one thread | Pass a unique `thread_id` per job invocation |
| Watch progress in real time | `.stream()` instead of `.invoke()` |
| Stream to UI | Iterate events, update `st.status()` or print to terminal |

---

**Next → [04-1 CLI](../04_serving_and_frontends/01_cli.md)**
