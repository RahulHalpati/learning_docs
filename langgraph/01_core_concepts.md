# 01: Core Concepts — State, Nodes, Edges, Reducers

> **Level:** Beginner  
> **Prerequisites:** Module 00 (Introduction)  
> **Time:** 1–2 hours  
> **What You'll Learn:** The four building blocks of every LangGraph application  
> **Last Updated:** 2026-05-05

---

## Introduction

**What:** The four fundamental primitives that every LangGraph application is built from — State, Nodes, Edges, and Reducers.  
**Why:** You cannot build anything in LangGraph without understanding these. Every agent, chatbot, and pipeline is a combination of these four concepts.  
**Analogy:** Think of a **board game** — the State is the game board (current positions, scores), Nodes are the actions players take, Edges are the rules for whose turn it is next, and Reducers define how scores get updated.

---

## Core Concepts

### Concept 1: State — The Shared Memory

**What:** A typed Python dictionary that flows through every node in your graph. It's the single source of truth.  
**Why:** Without shared state, nodes can't communicate. State carries context from one step to the next.

```python
from typing import TypedDict, Annotated
# What: TypedDict gives us typed dictionaries | Why: Type safety + IDE support
# What: Annotated lets us attach metadata (reducers) to types

from langgraph.graph import MessagesState
# What: Pre-built state with a 'messages' key | Why: Common pattern for chatbots

# === OPTION 1: Custom State (most flexible) ===
class ResearchState(TypedDict):
    query: str                    # The user's research question
    # Why: Immutable input — set once, read by all nodes

    sources: list[str]            # URLs/documents found
    # Why: Accumulates across multiple search nodes

    summary: str                  # Final synthesized answer
    # Why: The output — built progressively by LLM nodes

    iteration: int                # Loop counter
    # Why: Prevents infinite loops in research cycles


# === OPTION 2: Using MessagesState (for chat apps) ===
# MessagesState is equivalent to:
# class MessagesState(TypedDict):
#     messages: Annotated[list[AnyMessage], add_messages]
#
# The `add_messages` reducer automatically appends new messages
# instead of replacing the list — critical for conversation history
```

**Key Rules:**
- ✅ Use `TypedDict` or `Pydantic BaseModel` — always typed, never raw dicts
- ✅ Keep state minimal — only data that nodes actually need
- ❌ Don't store large temporary variables — use local function scope instead
- ❌ Don't use mutable defaults (e.g., `sources: list = []`)

---

### Concept 2: Nodes — The Workers

**What:** Python functions that receive the current state, do work, and return partial state updates.  
**Why:** Nodes are where actual logic happens — LLM calls, tool execution, data processing.

```python
from langchain_openai import ChatOpenAI
# What: OpenAI chat model wrapper | Why: Our LLM for generating responses
# Install: pip install langchain-openai

def search_node(state: ResearchState) -> dict:
    """
    What: Searches for sources related to the query.
    Why: Gathering information is the first step in research.

    Args:
        state (ResearchState): Current graph state with 'query' key
    Returns:
        dict: Partial state update — only the keys we're changing

    Note: We return a dict, NOT a full ResearchState.
          LangGraph merges our return into the existing state.
    """
    query = state["query"]

    # Simulate search (replace with real API in production)
    found_sources = [
        f"https://docs.example.com/{query.replace(' ', '-')}",
        f"https://wiki.example.com/{query.replace(' ', '-')}",
    ]

    # Return ONLY the keys we want to update
    # LangGraph handles the merge automatically
    return {
        "sources": found_sources,
        "iteration": state.get("iteration", 0) + 1
    }


def summarize_node(state: ResearchState) -> dict:
    """
    What: Uses an LLM to summarize the found sources.
    Why: Raw sources aren't useful — we need a synthesized answer.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # temperature=0: Deterministic output for consistent research summaries

    response = llm.invoke(
        f"Summarize findings about '{state['query']}' "
        f"from these sources: {state['sources']}"
    )

    return {"summary": response.content}
```

**Key Rules:**
- ✅ Each node does ONE thing well (Single Responsibility)
- ✅ Return partial state dicts — only keys you're changing
- ✅ Keep nodes as pure functions — same input → same output
- ❌ Don't modify state in-place — always return updates
- ❌ Don't put routing logic inside nodes — that's what edges are for

---

### Concept 3: Edges — The Traffic Directors

**What:** Connections between nodes that define execution order. Two types: fixed edges and conditional edges.  
**Why:** Edges control the flow — they decide which node runs next based on the current state.

```python
from typing import Literal
from langgraph.graph import StateGraph, START, END
# What: START and END are special sentinel nodes
# START = entry point of the graph
# END = terminal node (graph stops here)

# === Build the graph ===
builder = StateGraph(ResearchState)
# What: Creates a new graph builder with our state schema
# Why: Builder pattern — add nodes/edges, then compile once

# Register nodes
builder.add_node("search", search_node)
builder.add_node("summarize", summarize_node)

# --- FIXED EDGES ---
# Always go from START → search
builder.add_edge(START, "search")
# What: Unconditional connection | Why: Search always happens first

# --- CONDITIONAL EDGES ---
def should_continue(state: ResearchState) -> Literal["summarize", "search"]:
    """
    What: Decides whether to search again or move to summarization.
    Why: We may need multiple search iterations for complex queries.

    Returns:
        Literal string matching a node name (or END)
    """
    if state.get("iteration", 0) >= 3:
        return "summarize"     # Enough research, move on
    if len(state.get("sources", [])) < 3:
        return "search"        # Need more sources, loop back
    return "summarize"

builder.add_conditional_edges(
    "search",              # Source node: where we're coming FROM
    should_continue,       # Router function: inspects state, returns next node name
    {                      # Path map: maps return values → node names
        "summarize": "summarize",
        "search": "search",   # This creates a CYCLE (loop back)
    }
)

# Fixed edge: summarize → END (always finish after summarizing)
builder.add_edge("summarize", END)

# Compile — validates the graph and returns a runnable
graph = builder.compile()
```

**The Three Edge Types:**

| Type | Method | When to Use |
|------|--------|-------------|
| **Fixed** | `add_edge(A, B)` | A always leads to B, no exceptions |
| **Conditional** | `add_conditional_edges(source, router_fn, path_map)` | Next step depends on state |
| **Entry** | `add_edge(START, A)` | Defines where the graph begins |

---

### Concept 4: Reducers — The Merge Strategy

**What:** Functions that define HOW state updates get merged when a node returns new values.  
**Why:** Without reducers, returning `{"sources": ["new_url"]}` would **replace** the entire sources list. With a reducer, it can **append** instead.

```python
from typing import Annotated
from langgraph.graph import add_messages
# What: Built-in reducer that appends messages intelligently
# Why: Chat history should grow, not get replaced each turn

import operator
# What: Python's operator module | Why: operator.add is a simple list concatenator


# === State WITH reducers ===
class SmartState(TypedDict):
    query: str
    # No reducer → default behavior: REPLACE on update
    # If node returns {"query": "new"}, old query is overwritten

    sources: Annotated[list[str], operator.add]
    # Reducer: operator.add → APPEND new items to existing list
    # Node returns {"sources": ["url3"]} → sources becomes ["url1", "url2", "url3"]
    # Why: Multiple search nodes each contribute sources

    messages: Annotated[list, add_messages]
    # Reducer: add_messages → Smart append with deduplication
    # Why: Handles LangChain message objects, deduplicates by ID
    # This is what MessagesState uses internally

    iteration: int
    # No reducer → REPLACE (latest value wins)
    # Why: We always want the current count, not accumulated


# === How reducers work in practice ===
# Initial state:  {"sources": ["url1", "url2"], "iteration": 1}
# Node returns:   {"sources": ["url3"], "iteration": 2}
#
# WITHOUT reducer on sources: {"sources": ["url3"], "iteration": 2}  ← url1, url2 LOST!
# WITH operator.add reducer:  {"sources": ["url1", "url2", "url3"], "iteration": 2}  ✅
```

**Built-in Reducers:**

| Reducer | Import | Behavior |
|---------|--------|----------|
| `operator.add` | `import operator` | Concatenates lists |
| `add_messages` | `from langgraph.graph import add_messages` | Appends messages, deduplicates by ID |
| None (default) | — | Replaces value entirely |
| Custom function | Define your own | Any merge logic you need |

**Custom Reducer Example:**
```python
def merge_unique(existing: list[str], new: list[str]) -> list[str]:
    """
    What: Merges two lists, keeping only unique values.
    Why: Prevents duplicate sources from multiple search iterations.
    """
    return list(set(existing + new))

class DeduplicatedState(TypedDict):
    sources: Annotated[list[str], merge_unique]
    # Now duplicate URLs are automatically removed on merge
```

---

## Practical Example: Putting It All Together

**Building:** A simple research pipeline that searches, evaluates, and summarizes  
**Why:** Demonstrates all four concepts working together

```python
"""
research_pipeline.py
What: A complete LangGraph pipeline that researches a topic
Why: Demonstrates State + Nodes + Edges + Reducers in one working example
"""

# STANDARD LIBRARY
from typing import TypedDict, Annotated, Literal
import operator  # What: Provides operator.add for list concatenation

# THIRD-PARTY
from langgraph.graph import StateGraph, START, END
# What: Core graph building blocks
# Why: StateGraph = builder, START/END = entry/exit sentinels

from langchain_openai import ChatOpenAI
# What: OpenAI wrapper | Why: Our LLM | Install: pip install langchain-openai


# ──────────────────────────────────────────────
# 1. STATE — Define the data flowing through
# ──────────────────────────────────────────────
class PipelineState(TypedDict):
    topic: str                                          # Input: what to research
    findings: Annotated[list[str], operator.add]        # Accumulates across nodes
    quality_score: float                                # Set by evaluator
    final_report: str                                   # Output: the answer


# ──────────────────────────────────────────────
# 2. NODES — Define the work
# ──────────────────────────────────────────────
def research(state: PipelineState) -> dict:
    """Searches for information on the topic."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    result = llm.invoke(f"List 3 key facts about: {state['topic']}")
    return {"findings": [result.content]}


def evaluate(state: PipelineState) -> dict:
    """Scores the quality of findings (0.0 to 1.0)."""
    # Simple heuristic: more content = higher quality
    total_length = sum(len(f) for f in state["findings"])
    score = min(total_length / 500, 1.0)
    return {"quality_score": score}


def write_report(state: PipelineState) -> dict:
    """Produces the final summary report."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
    result = llm.invoke(
        f"Write a concise report about '{state['topic']}' "
        f"using these findings:\n{chr(10).join(state['findings'])}"
    )
    return {"final_report": result.content}


# ──────────────────────────────────────────────
# 3. EDGES — Define the flow
# ──────────────────────────────────────────────
def quality_gate(state: PipelineState) -> Literal["research", "write_report"]:
    """Routes based on quality: loop back if insufficient, proceed if good."""
    if state.get("quality_score", 0) < 0.6:
        return "research"      # Not enough info, search again
    return "write_report"      # Good enough, write the report


# ──────────────────────────────────────────────
# 4. BUILD & COMPILE
# ──────────────────────────────────────────────
builder = StateGraph(PipelineState)

# Add nodes
builder.add_node("research", research)
builder.add_node("evaluate", evaluate)
builder.add_node("write_report", write_report)

# Add edges
builder.add_edge(START, "research")           # Always start with research
builder.add_edge("research", "evaluate")      # Always evaluate after research
builder.add_conditional_edges(                # Conditional: loop or proceed
    "evaluate",
    quality_gate,
    {"research": "research", "write_report": "write_report"}
)
builder.add_edge("write_report", END)         # Always end after report

# Compile
pipeline = builder.compile()


# ──────────────────────────────────────────────
# 5. EXECUTE
# ──────────────────────────────────────────────
if __name__ == "__main__":
    result = pipeline.invoke({
        "topic": "Benefits of RAG in enterprise AI",
        "findings": [],         # Start empty — reducer will accumulate
        "quality_score": 0.0,
        "final_report": ""
    })

    print("=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(result["final_report"])
    print(f"\nQuality Score: {result['quality_score']:.2f}")
    print(f"Findings collected: {len(result['findings'])}")
```

**Expected Output:**
```
============================================================
FINAL REPORT
============================================================
[A concise report about RAG benefits in enterprise AI...]

Quality Score: 0.85
Findings collected: 2
```

---

## Best Practices

**✅ DO:**
- Use `TypedDict` for state — Why: Type safety catches errors at development time
- Keep nodes focused on one task — Why: Easier to test, debug, and reuse
- Use reducers for list/accumulating fields — Why: Prevents accidental data loss
- Return partial state dicts from nodes — Why: LangGraph handles the merge

**❌ DON'T:**
- Put routing logic inside nodes — Why bad: Violates separation of concerns | Fix: Use conditional edges
- Use raw dicts for state — Why bad: No type checking, no IDE support | Fix: Always use TypedDict
- Mutate state in-place — Why bad: Breaks checkpointing and replay | Fix: Return new values
- Store large blobs in state — Why bad: Serialized on every checkpoint | Fix: Use references/IDs

---

## Common Mistakes

**Mistake 1: Forgetting a reducer on list fields**
```python
# ❌ BAD — sources gets REPLACED each time
class BadState(TypedDict):
    sources: list[str]

# Node 1 returns: {"sources": ["a", "b"]}  → sources = ["a", "b"]
# Node 2 returns: {"sources": ["c"]}        → sources = ["c"]  ← "a", "b" GONE!
```
**Fix:**
```python
# ✅ GOOD — sources gets APPENDED
class GoodState(TypedDict):
    sources: Annotated[list[str], operator.add]

# Node 1 returns: {"sources": ["a", "b"]}  → sources = ["a", "b"]
# Node 2 returns: {"sources": ["c"]}        → sources = ["a", "b", "c"]  ✅
```

**Mistake 2: Returning full state instead of partial updates**
```python
# ❌ BAD — overwrites everything, verbose, error-prone
def bad_node(state: MyState) -> MyState:
    return {"query": state["query"], "results": ["new"], "count": state["count"] + 1}

# ✅ GOOD — only return what changed
def good_node(state: MyState) -> dict:
    return {"results": ["new"], "count": state["count"] + 1}
```

---

## Practice Exercises

**Exercise 1:** Build a two-node graph where Node A generates a random number and Node B classifies it as "even" or "odd". Use a conditional edge to route to different END messages.

- Requirements: TypedDict state, two nodes, one conditional edge
- Hint: The router function should check `state["number"] % 2`

<details>
<summary>Solution</summary>

```python
import random
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class NumberState(TypedDict):
    number: int
    result: str

def generate(state: NumberState) -> dict:
    return {"number": random.randint(1, 100)}

def classify_even(state: NumberState) -> dict:
    return {"result": f"{state['number']} is EVEN"}

def classify_odd(state: NumberState) -> dict:
    return {"result": f"{state['number']} is ODD"}

def route(state: NumberState) -> Literal["even", "odd"]:
    return "even" if state["number"] % 2 == 0 else "odd"

builder = StateGraph(NumberState)
builder.add_node("generate", generate)
builder.add_node("even", classify_even)
builder.add_node("odd", classify_odd)

builder.add_edge(START, "generate")
builder.add_conditional_edges("generate", route, {"even": "even", "odd": "odd"})
builder.add_edge("even", END)
builder.add_edge("odd", END)

graph = builder.compile()
print(graph.invoke({"number": 0, "result": ""}))
```
**Why it works:** The conditional edge inspects state after generation and routes to the correct classifier.
</details>

---

## What's Next

**Learned:** ✅ State (TypedDict), ✅ Nodes (worker functions), ✅ Edges (fixed + conditional), ✅ Reducers (merge strategies)  
**Next:** Module 02: Architecture & Internals — How StateGraph works under the hood, the compile/invoke lifecycle, and mental models  
**Check:** Can you explain why a reducer is needed on a `list` field? Can you draw a graph with a loop?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-05 | Initial creation |
