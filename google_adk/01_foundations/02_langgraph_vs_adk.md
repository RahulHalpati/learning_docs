# 01-2 · LangGraph vs ADK — the bridge

> **Level:** Beginner · **Prerequisites:** [01-1 · Architecture & primitives](01_architecture_and_primitives.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (concepts)

## Why this matters

Two of the best agent frameworks, two different philosophies. If you know [LangGraph](../../langgraph/), this lesson maps every concept across so your knowledge transfers. If you don't, it still gives you the clearest one-page picture of what makes ADK *ADK*.

> A project-angle comparison also lives in the Faceless YouTube course: [`faceless_youtube_agent/01_foundations/02_langgraph_vs_google_adk.md`](../../faceless_youtube_agent/01_foundations/02_langgraph_vs_google_adk.md). This lesson is the framework-deep version.

---

## The one-sentence difference

- **LangGraph** — you **draw a graph**: `state → nodes → edges`. Control flow is explicit and visible; you decide exactly what runs next.
- **ADK** — you **compose agents**: an `LlmAgent` for reasoning, wrapped in `Sequential`/`Parallel`/`Loop` agents for orchestration. Control flow is expressed by *nesting agents*.

Both are Python-first, open source, model-agnostic, and do multi-agent + human oversight. They overlap heavily; the *shape of your code* is what differs.

---

## Concept map

| Concept | LangGraph | Google ADK |
|---------|-----------|------------|
| Core unit | a **node** (function) in a `StateGraph` | an **`LlmAgent`** |
| Orchestration | **edges** (fixed/conditional) + `Command`/`Send` | **workflow agents** (`Sequential`/`Parallel`/`Loop`) + delegation |
| Shared data | typed **state** + reducers | **`Session.state`** dict (+ `output_key`) |
| Short-term memory | **checkpointer** + `thread_id` | **`SessionService`** + session id |
| Long-term memory | the **store** (`BaseStore`) | **`MemoryService`** |
| Tools | `@tool` + `ToolNode` | `FunctionTool` / OpenAPI / MCP tools |
| Running it | `graph.invoke/stream` | `Runner.run_async` yielding **events** |
| Human-in-the-loop | `interrupt()` / `Command(resume=)` | long-running tools / callbacks / `interrupt` |
| Parallel fan-out | **`Send`** map-reduce | **`ParallelAgent`** |
| Loops | cyclic edges + `recursion_limit` | **`LoopAgent`** (`max_iterations`) + escalation |
| Multi-agent handoff | `Command(goto=..., graph=PARENT)` | **sub-agent transfer** / `transfer_to_agent` |
| Deploy | LangGraph Platform / Server | Vertex **Agent Engine** / Cloud Run / GKE |
| Observability | LangSmith | ADK eval + Cloud tracing |
| Cross-agent protocol | (via tools/APIs) | first-class **A2A** |

---

## Same job, two shapes

A fixed pipeline "research → write":

**LangGraph** (wire the graph):
```python
b = StateGraph(State)
b.add_node("research", research); b.add_node("write", write)
b.add_edge(START, "research"); b.add_edge("research", "write"); b.add_edge("write", END)
graph = b.compile()
```

**ADK** (compose agents):
```python
from google.adk.agents import SequentialAgent, LlmAgent
pipeline = SequentialAgent(
    name="pipeline",
    sub_agents=[researcher, writer],   # each an LlmAgent
)
```

LangGraph makes the *wiring* visible (great for learning and complex branching); ADK makes the *composition* concise (great when steps are mostly LLM agents). Neither is "better" — they optimize for different things.

---

## When to reach for which

| Prefer LangGraph when | Prefer ADK when |
|---|---|
| control flow is intricate (many conditional branches, cycles, map-reduce) and you want to *see* it | your app is mostly LLM agents composed in order/parallel/loops |
| you're already in the LangChain ecosystem | you're on Google Cloud / standardizing on Gemini |
| you want fine-grained state + reducers | you want batteries-included eval, memory services, and A2A |

The concepts transfer both ways — the capstones in both courses build the *same* research assistant so you can compare line for line.

---

## Recap & next

- ✅ LangGraph = **draw a graph**; ADK = **compose agents**. Same capabilities, different code shape.
- ✅ The concept map translates state/memory/tools/loops/handoffs/deploy across both.
- ✅ Choose by control-flow complexity and ecosystem, not by "which is better".
- ✅ Self-check: what's ADK's equivalent of LangGraph's `Send` map-reduce, and of a checkpointer?

→ Next: **[01-3 · Environment & offline models](03_environment_and_offline_models.md)**

## Exercises

1. Without looking, write ADK's equivalent for: a LangGraph *conditional edge*, a *reducer-accumulated list*, and *`interrupt()`*.

<details>
<summary>Solution</summary>

Conditional edge → an `LlmAgent` deciding to `transfer_to_agent` (or a custom agent's branching); reducer list → appending to a `Session.state` list yourself (ADK state has no reducer concept — you merge in code); `interrupt()` → a long-running tool / callback that pauses for input. The mappings are close but not 1:1 — that's the value of knowing both.
</details>
