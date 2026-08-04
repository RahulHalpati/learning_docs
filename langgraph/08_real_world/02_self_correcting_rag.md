# 08-2 · Self-correcting RAG

> **Level:** Intermediate · **Prerequisites:** [04-1 · Conditional edges](../04_control_flow/01_conditional_edges.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langchain-core 1.5.0)

## Why this matters

A plain RAG chain is "retrieve → generate → done" — fire and forget, no quality control. Wrapping it in a LangGraph loop adds a **self-evaluation** step: the graph judges its own answer and, if it's weak, retrieves more and tries again. That loop is the difference between a demo that sometimes hallucinates and an assistant that knows when it hasn't answered.

> This pairs with the [LangChain & RAG](../../langchain_rag/) guide — that course builds the retrieval/embeddings; this one adds the *control loop* around it.

```mermaid
flowchart LR
    START(["START"]) --> R[retrieve] --> G[generate] --> E[evaluate]
    E -->|retry| R
    E -->|good| END(["END"])
```

---

## The loop (offline, deterministic)

The generator is scripted to return two weak answers then a good one — so you can *see* the correction loop fire twice. Evaluation and the attempt cap bound it.

```python
from typing import TypedDict, Annotated, Literal
import operator
from langgraph.graph import StateGraph, START, END
from langchain_core.language_models.fake_chat_models import FakeListChatModel

gen_llm = FakeListChatModel(responses=["weak answer", "weak answer",
                                       "grounded answer with citations"])

class RAGState(TypedDict):
    question: str
    docs: Annotated[list[str], operator.add]
    answer: str
    quality: str
    attempt: int

def retrieve(s): return {"docs": [f"doc for attempt {s.get('attempt', 0) + 1}"],
                         "attempt": s.get("attempt", 0) + 1}
def generate(s): return {"answer": gen_llm.invoke(s["question"]).content}
def evaluate(s): return {"quality": "good" if "grounded" in s["answer"] else "retry"}

def quality_router(s) -> Literal["retrieve", "end"]:
    if s["quality"] == "good" or s["attempt"] >= 3:   # cap attempts as a safety net
        return "end"
    return "retrieve"

b = StateGraph(RAGState)
for n, f in [("retrieve", retrieve), ("generate", generate), ("evaluate", evaluate)]:
    b.add_node(n, f)
b.add_edge(START, "retrieve"); b.add_edge("retrieve", "generate"); b.add_edge("generate", "evaluate")
b.add_conditional_edges("evaluate", quality_router, {"retrieve": "retrieve", "end": END})

out = b.compile().invoke({"question": "how does persistence work?",
                          "docs": [], "answer": "", "quality": "", "attempt": 0})
print("answer:", out["answer"], "| attempts:", out["attempt"])
```

**Output (real run):**
```
answer: grounded answer with citations | attempts: 3
```

Three passes: two produced "weak answer" → `evaluate` said `retry` → back to `retrieve`; the third produced a grounded answer → `end`. The `attempt >= 3` guard guarantees termination even if the answer never satisfies the evaluator.

> **Tip:** In production the "evaluator" is often a second LLM call (an *LLM-as-judge*) checking the answer against the retrieved docs — or a groundedness score. Whatever the check, the graph shape is the same; only the `evaluate` node changes. And always keep an attempt cap, or a stubborn evaluator loops forever.

---

## Why a graph beats a chain here

| | Plain RAG chain | Self-correcting graph |
|---|---|---|
| Quality control | none | self-evaluation loop |
| Bad retrieval | returned as-is | triggers re-retrieval |
| Termination | one pass | "good" *or* attempt cap |

---

## Recap & next

- ✅ retrieve → generate → **evaluate** → loop back or finish is the self-correction pattern.
- ✅ Always bound the loop (attempt counter and/or `recursion_limit`).
- ✅ The evaluator is a swappable node — heuristic, LLM-judge, or groundedness score.
- ✅ Self-check: what guarantees this graph terminates even if `evaluate` never returns "good"?

→ Next: **[08-3 · DevOps pipeline](03_devops_pipeline.md)**

## Exercises

1. Add query *refinement*: on each retry, `retrieve` should broaden the query (e.g. append "detailed") so later attempts differ from earlier ones.

<details>
<summary>Solution</summary>

Track a `query` in state; in `retrieve`, on `attempt > 1` set `query = base + " (broadened)"` and retrieve against that. This models the real benefit of the loop — *different* retrievals each pass, not identical ones.
</details>
