# 01-1 · Core concepts — state, nodes, edges, reducers

> **Level:** Beginner · **Prerequisites:** [00 · Introduction](../00_introduction.md)
> **Time:** 45 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langchain-core 1.5.0, Python 3.10)

## Why this matters

You cannot build *anything* in LangGraph without these four primitives. Every agent, chatbot, and pipeline in this course is a recombination of **State**, **Nodes**, **Edges**, and **Reducers**. Get these four right and the rest of LangGraph is just more of the same.

> **Analogy — a board game.** The **state** is the board (positions, scores). **Nodes** are the moves players make. **Edges** are the rules for whose turn is next. **Reducers** define how scores get updated when a move happens.

---

## 1. State — the shared memory

State is a **typed dictionary** that flows through every node. It's the single source of truth; without it, nodes couldn't communicate.

```python
from typing import TypedDict, Annotated
import operator

class ResearchState(TypedDict):
    query: str                                  # input: set once, read by all nodes
    sources: Annotated[list[str], operator.add] # accumulates across nodes (see Reducers)
    summary: str                                # output: built progressively
    iteration: int                              # loop counter to bound cycles
```

**Rules of thumb**

- ✅ Use `TypedDict` (or a Pydantic `BaseModel` when you want validation) — never a raw untyped `dict`.
- ✅ Keep state minimal: only data nodes actually need.
- ❌ Don't stuff large blobs in state — it's serialized on every checkpoint. Store a reference/id instead.

---

## 2. Nodes — the workers

A node is a **function** that receives the current state, does work, and returns a **partial** update — only the keys it changes. LangGraph merges that update into the state for you.

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)   # reads OPENAI_API_KEY

def search_node(state: ResearchState) -> dict:
    """Gather sources for the query. Returns ONLY the keys it changes."""
    query = state["query"]
    found = [f"https://docs.example.com/{query.replace(' ', '-')}"]
    return {"sources": found, "iteration": state.get("iteration", 0) + 1}

def summarize_node(state: ResearchState) -> dict:
    """Synthesize a summary from the gathered sources."""
    resp = llm.invoke(f"Summarize {state['query']} from {state['sources']}")
    return {"summary": resp.content}
```

**Rules of thumb**

- ✅ One node, one job. Easier to test, debug, reuse.
- ✅ Return a partial dict — never mutate `state` in place (that breaks checkpointing/replay).
- ❌ No routing logic inside nodes. Deciding *what runs next* is the edge's job.

---

## 3. Edges — the traffic directors

Edges connect nodes and define execution order. Three kinds:

| Type | Method | When |
|------|--------|------|
| **Entry** | `add_edge(START, "a")` | Where the graph begins |
| **Fixed** | `add_edge("a", "b")` | `a` always leads to `b` |
| **Conditional** | `add_conditional_edges("a", router, path_map)` | Next step depends on state |

A conditional edge is just a function that reads state and returns a *string* naming the next node (or `END`):

```python
from typing import Literal

def should_continue(state: ResearchState) -> Literal["summarize", "search"]:
    if state.get("iteration", 0) >= 3:        # bound the loop
        return "summarize"
    if len(state.get("sources", [])) < 3:
        return "search"                        # loop back — this creates a CYCLE
    return "summarize"
```

> **Tip:** Cycles are legal and encouraged — they're how agents "try again". Just make sure a counter (or the built-in `recursion_limit`, see [02-3](../02_execution_model/03_durability_retries_caching.md)) can end the loop.

---

## 4. Reducers — the merge strategy

A reducer decides **how** a node's update is merged into state. Without one, returning `{"sources": ["new"]}` **replaces** the whole list. With `operator.add`, it **appends**.

```python
from langgraph.graph import add_messages

class SmartState(TypedDict):
    query: str                                    # no reducer → REPLACE (latest wins)
    sources: Annotated[list[str], operator.add]   # → APPEND
    messages: Annotated[list, add_messages]       # → smart append, dedup by id
    iteration: int                                # no reducer → REPLACE
```

What actually happens on merge:

```
Before:       {"sources": ["url1", "url2"], "iteration": 1}
Node returns: {"sources": ["url3"],         "iteration": 2}

no reducer   → {"sources": ["url3"], "iteration": 2}                 # url1, url2 LOST
operator.add → {"sources": ["url1","url2","url3"], "iteration": 2}   # ✅
```

| Reducer | Import | Behavior |
|---------|--------|----------|
| `operator.add` | `import operator` | Concatenate lists |
| `add_messages` | `from langgraph.graph import add_messages` | Append messages, dedup by id |
| *none* (default) | — | Replace the value entirely |
| custom fn | you write it | Any merge logic |

A custom reducer is just a two-argument function `(existing, new) -> merged`:

```python
def merge_unique(existing: list[str], new: list[str]) -> list[str]:
    return list(dict.fromkeys((existing or []) + new))   # dedup, preserve order

class DedupState(TypedDict):
    sources: Annotated[list[str], merge_unique]
```

---

## All four together (runnable)

A research pipeline that loops until it has enough findings, then writes a report:

```python
from typing import TypedDict, Annotated, Literal
import operator
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

class PipelineState(TypedDict):
    topic: str
    findings: Annotated[list[str], operator.add]   # accumulate across loops
    quality_score: float
    final_report: str

def research(state):     return {"findings": [llm.invoke(f"State one fact about {state['topic']}, in one sentence.").content]}
def evaluate(state):     return {"quality_score": min(len(state["findings"]) / 2, 1.0)}   # 2 findings = good enough
def write_report(state): return {"final_report": llm.invoke("Write a two-sentence report from these findings:\n" + "\n".join(state["findings"])).content}

def quality_gate(state) -> Literal["research", "write_report"]:
    return "research" if state.get("quality_score", 0) < 0.6 else "write_report"

builder = StateGraph(PipelineState)
builder.add_node("research", research)
builder.add_node("evaluate", evaluate)
builder.add_node("write_report", write_report)
builder.add_edge(START, "research")
builder.add_edge("research", "evaluate")
builder.add_conditional_edges("evaluate", quality_gate,
                              {"research": "research", "write_report": "write_report"})
builder.add_edge("write_report", END)
pipeline = builder.compile()

result = pipeline.invoke({"topic": "RAG in enterprise AI", "findings": [],
                          "quality_score": 0.0, "final_report": ""})
print("REPORT:", result["final_report"])
print(f"Quality: {result['quality_score']:.2f} · Findings: {len(result['findings'])}")
```

**Output (representative — your wording will differ):**
```
REPORT: RAG improves enterprise AI by grounding answers in an organisation's own documents, which reduces hallucinations. It also makes answers auditable through citations to the retrieved sources.
Quality: 1.00 · Findings: 2
```

Notice `Findings: 2` — the first pass scored below `0.6`, so `quality_gate` routed **back** to `research` (a cycle), and the `operator.add` reducer *accumulated* the second finding instead of overwriting the first. That's all four primitives in one run.

---

## Recap & next

- ✅ **State** = typed shared dict; **Nodes** = functions returning partial updates; **Edges** = routing (fixed/conditional/entry); **Reducers** = how updates merge.
- ✅ List fields almost always need a reducer (`operator.add` / `add_messages`) or you'll silently lose data.
- ✅ Cycles are how agents retry — bound them with a counter or `recursion_limit`.
- ✅ Self-check: why does `findings` end at 2 and not 1? What would happen without `operator.add`?

→ Next: **[01-2 · State & messages](02_state_and_messages.md)**

## Exercises

1. Build a two-node graph: node A stores a random integer in state; node B classifies it "even"/"odd" via a **conditional edge** to two different terminal nodes.

<details>
<summary>Solution</summary>

```python
import random
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class NumState(TypedDict):
    number: int
    result: str

def generate(state): return {"number": random.randint(1, 100)}
def even(state):     return {"result": f"{state['number']} is EVEN"}
def odd(state):      return {"result": f"{state['number']} is ODD"}
def route(state) -> Literal["even", "odd"]:
    return "even" if state["number"] % 2 == 0 else "odd"

b = StateGraph(NumState)
b.add_node("generate", generate); b.add_node("even", even); b.add_node("odd", odd)
b.add_edge(START, "generate")
b.add_conditional_edges("generate", route, {"even": "even", "odd": "odd"})
b.add_edge("even", END); b.add_edge("odd", END)
print(b.compile().invoke({"number": 0, "result": ""}))
```
The conditional edge inspects state *after* `generate` and routes to the right classifier.
</details>

2. Change `findings` in the pipeline above to a plain `list[str]` (no reducer) and predict, then verify, what `len(result['findings'])` becomes.

<details>
<summary>Solution</summary>

It becomes **1**. Without `operator.add`, each `research` return *replaces* the list, so only the last loop's finding survives — the classic "forgot the reducer" bug.
</details>
