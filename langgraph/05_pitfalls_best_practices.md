# 05: Pitfalls & Best Practices

> **Level:** Intermediate  
> **Prerequisites:** Modules 00–04  
> **Time:** 45–60 minutes  
> **What You'll Learn:** Common mistakes, performance tips, scaling strategies, and production hardening  
> **Last Updated:** 2026-05-05

---

## Introduction

**What:** The mistakes developers make most often with LangGraph, and the practices that prevent them.  
**Why:** The gap between "works in a notebook" and "works in production" is where projects fail. This module bridges that gap.

---

## ⚠️ Common Mistakes

### Mistake 1: Untyped State (Raw Dicts)

```python
# ❌ BAD — no type safety, no IDE autocomplete, silent bugs
graph = StateGraph(dict)

def my_node(state):
    return {"resutls": state["query"]}  # Typo in "results" — no error!
```

**Why it breaks:** Typos silently create new keys. You'll spend hours debugging why `state["results"]` is empty.

```python
# ✅ GOOD — TypedDict catches issues at development time
from typing import TypedDict

class MyState(TypedDict):
    query: str
    results: list[str]  # IDE will autocomplete this

graph = StateGraph(MyState)

def my_node(state: MyState) -> dict:
    return {"results": ["found"]}  # Typo → your linter/IDE warns you
```

---

### Mistake 2: Missing Reducers on Accumulating Fields

```python
# ❌ BAD — second node overwrites first node's results
class BadState(TypedDict):
    search_results: list[str]

# Node A returns: {"search_results": ["result1"]}  → OK
# Node B returns: {"search_results": ["result2"]}  → ["result1"] is GONE
```

```python
# ✅ GOOD — operator.add merges lists
import operator
from typing import Annotated

class GoodState(TypedDict):
    search_results: Annotated[list[str], operator.add]

# Node A returns: {"search_results": ["result1"]}
# Node B returns: {"search_results": ["result2"]}
# Final state:    {"search_results": ["result1", "result2"]}  ✅
```

---

### Mistake 3: Infinite Loops Without Safety Bounds

```python
# ❌ BAD — no loop counter, can run forever
def should_retry(state):
    if state["quality"] < 0.8:
        return "retry"  # Could loop infinitely!
    return "done"
```

```python
# ✅ GOOD — always cap loop iterations
def should_retry(state) -> Literal["retry", "done"]:
    MAX_RETRIES = 3  # Hard safety limit
    if state["quality"] < 0.8 and state.get("attempt", 0) < MAX_RETRIES:
        return "retry"
    return "done"  # Stop even if quality is low
```

**Rule of thumb:** Every conditional edge that can loop back MUST have a counter or timeout.

---

### Mistake 4: Using MemorySaver in Production

```python
# ❌ BAD — all state lost on server restart
from langgraph.checkpoint.memory import MemorySaver
graph = builder.compile(checkpointer=MemorySaver())
# Fine for development/testing, NEVER for production
```

```python
# ✅ GOOD — persistent storage that survives restarts
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://user:pass@db-host:5432/langgraph"
with PostgresSaver.from_conn_string(DB_URI) as saver:
    saver.setup()  # Run once to create tables
    graph = builder.compile(checkpointer=saver)
```

---

### Mistake 5: Putting Routing Logic Inside Nodes

```python
# ❌ BAD — node decides its own next step (violates separation of concerns)
def my_node(state):
    if some_condition:
        return {"next": "node_a", "data": "..."}
    return {"next": "node_b", "data": "..."}
```

```python
# ✅ GOOD — nodes do work, edges decide flow
def my_node(state) -> dict:
    """Does work only — returns state updates."""
    return {"data": process(state)}

def route_decision(state) -> Literal["node_a", "node_b"]:
    """Decides flow only — no side effects."""
    if state["data"].score > 0.8:
        return "node_a"
    return "node_b"

builder.add_conditional_edges("my_node", route_decision, {...})
```

---

### Mistake 6: Forgetting `thread_id` with Checkpointers

```python
# ❌ BAD — all users share the same conversation!
graph.invoke({"messages": [("user", "Hi")]})  # No config → no thread isolation
```

```python
# ✅ GOOD — unique thread per conversation
config = {"configurable": {"thread_id": f"user-{user_id}-{session_id}"}}
graph.invoke({"messages": [("user", "Hi")]}, config=config)
```

---

## 🏋️ Performance Considerations

### 1. State Size Matters

```python
# ❌ BAD — storing full documents in state (serialized every checkpoint)
class HeavyState(TypedDict):
    full_documents: list[str]  # Could be MB of text
    embeddings: list[list[float]]  # Huge numerical arrays

# ✅ GOOD — store references, not data
class LightState(TypedDict):
    document_ids: list[str]        # Just IDs — fetch when needed
    embedding_index: str           # Reference to vector store
```

**Why:** State is serialized/deserialized at every checkpoint. Large state = slow execution.

### 2. Parallelize Independent Nodes

```python
# If two nodes don't depend on each other's output,
# LangGraph can run them in parallel:

# These nodes are INDEPENDENT — they read different state keys
builder.add_node("search_web", search_web)
builder.add_node("search_db", search_db)

# Fan-out from a single node
builder.add_edge("classifier", "search_web")
builder.add_edge("classifier", "search_db")

# Fan-in to a single node (waits for both to complete)
builder.add_edge("search_web", "synthesize")
builder.add_edge("search_db", "synthesize")
```

### 3. Use Streaming for Long Operations

```python
# Don't wait for the entire graph to complete — stream intermediate results

# Stream node-by-node updates
for event in graph.stream(input, stream_mode="updates"):
    node_name = list(event.keys())[0]
    print(f"✅ {node_name} completed")

# Stream token-by-token (for LLM responses)
async for event in graph.astream_events(input, version="v2"):
    if event["event"] == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="", flush=True)
```

### 4. Async All the Way

```python
# ❌ BAD — synchronous LLM calls block the event loop
def slow_node(state):
    result = llm.invoke(state["messages"])  # Blocking!
    return {"messages": [result]}

# ✅ GOOD — async nodes for I/O-bound work
async def fast_node(state):
    result = await llm.ainvoke(state["messages"])  # Non-blocking
    return {"messages": [result]}

# Use ainvoke for the graph too
result = await graph.ainvoke(input, config)
```

---

## 🔒 Production Hardening

### 1. Input Validation

```python
from pydantic import BaseModel, field_validator

class ValidatedInput(BaseModel):
    """Validates input before it enters the graph."""
    query: str
    customer_id: str

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        if len(v) > 5000:
            raise ValueError("Query too long (max 5000 chars)")
        return v.strip()


# Validate before invoking
try:
    validated = ValidatedInput(query=user_input, customer_id=cid)
    result = graph.invoke({"query": validated.query, ...})
except ValueError as e:
    return {"error": str(e)}
```

### 2. Error Handling in Nodes

```python
def resilient_node(state):
    """Node with proper error handling."""
    try:
        result = external_api_call(state["query"])
        return {"result": result, "error": None}
    except TimeoutError:
        return {"result": None, "error": "API timeout — retrying..."}
    except Exception as e:
        return {"result": None, "error": f"Unexpected: {str(e)}"}
```

### 3. Observability with LangSmith

```python
# Set environment variables to enable tracing
import os
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "ls-your-key"
os.environ["LANGSMITH_PROJECT"] = "my-langgraph-app"

# Now every graph.invoke() is automatically traced
# View traces at: https://smith.langchain.com
# You get: node execution times, state at each step, LLM inputs/outputs
```

### 4. Rate Limiting

```python
import time
from functools import wraps

def rate_limit(max_calls_per_minute: int = 30):
    """Decorator to rate-limit node execution."""
    interval = 60.0 / max_calls_per_minute
    last_call = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(state):
            elapsed = time.time() - last_call[0]
            if elapsed < interval:
                time.sleep(interval - elapsed)
            last_call[0] = time.time()
            return func(state)
        return wrapper
    return decorator

@rate_limit(max_calls_per_minute=20)
def llm_node(state):
    """Rate-limited LLM call — prevents API quota exhaustion."""
    return {"response": llm.invoke(state["messages"])}
```

---

## 📋 Production Checklist

| Category | Check | Status |
|----------|-------|--------|
| **State** | TypedDict or Pydantic for all state | ☐ |
| **State** | Reducers on all accumulating fields | ☐ |
| **Safety** | Max iteration limits on all loops | ☐ |
| **Safety** | Input validation before graph entry | ☐ |
| **Safety** | Error handling in every node | ☐ |
| **Persistence** | PostgresSaver (not MemorySaver) | ☐ |
| **Persistence** | Unique thread_id per conversation | ☐ |
| **HITL** | interrupt() before destructive actions | ☐ |
| **Performance** | State contains references, not blobs | ☐ |
| **Performance** | Async nodes for I/O operations | ☐ |
| **Observability** | LangSmith tracing enabled | ☐ |
| **Observability** | Structured logging in nodes | ☐ |
| **Security** | Sanitize inputs, scrub PII from logs | ☐ |

---

## What's Next

**Learned:** ✅ 6 critical mistakes to avoid, ✅ Performance patterns, ✅ Production hardening, ✅ Deployment checklist  
**Next:** Module 06: Connections & Ecosystem — How LangGraph relates to agents, RAG, tools, memory  
**Check:** Can you audit one of your graphs against the production checklist?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-05 | Initial creation |
