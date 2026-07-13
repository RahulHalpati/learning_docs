# 02: Architecture & How It Works

> **Level:** Beginner → Intermediate  
> **Prerequisites:** Module 01 (Core Concepts)  
> **Time:** 1–1.5 hours  
> **What You'll Learn:** Internal lifecycle, compile vs invoke, graph execution model, checkpointing  
> **Last Updated:** 2026-05-05

---

## Introduction

**What:** How LangGraph executes your graph internally — from `compile()` to `invoke()` to final output.  
**Why:** Understanding the execution model prevents debugging nightmares and helps you design efficient graphs.  
**Analogy:** Think of a **compiled program** — you write source code (add nodes/edges), compile it (validate + optimize), then run it (invoke). LangGraph works the same way.

---

## The Two-Phase Lifecycle

### Phase 1: Build Time (`StateGraph` → `compile()`)

```
 You write code:                    LangGraph validates:
 ┌──────────────┐                  ┌─────────────────────────┐
 │ add_node()   │                  │ ✓ All nodes reachable   │
 │ add_edge()   │ ── compile() ──▶ │ ✓ No dangling edges     │
 │ add_cond..() │                  │ ✓ State schema valid    │
 └──────────────┘                  │ ✓ START has an edge     │
                                   │ ✓ At least one path→END │
                                   └─────────┬───────────────┘
                                             │
                                             ▼
                                   CompiledGraph (Runnable)
```

**What happens at `compile()`:**
1. **Validates** the graph structure (unreachable nodes, missing edges)
2. **Freezes** the topology — no more modifications after this
3. **Attaches** checkpointer if provided (for persistence)
4. **Returns** a `CompiledGraph` object that implements LangChain's `Runnable` interface

```python
# After compile(), you get a Runnable with these methods:
graph = builder.compile()

graph.invoke(input)          # Synchronous, returns final state
await graph.ainvoke(input)   # Async version

# Streaming (get intermediate results as they happen)
for event in graph.stream(input):
    print(event)             # Each node's output as it completes

# Stream with full event detail
async for event in graph.astream_events(input, version="v2"):
    print(event)             # Fine-grained: token-by-token streaming
```

---

### Phase 2: Runtime (`invoke()` execution)

```
invoke({"topic": "AI"})
        │
        ▼
┌─────────────────┐
│  Load initial    │
│  state           │◄─── Your input merged with defaults
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│  START           │
│  (entry point)   │
└───────┬─────────┘
        │ (follow edge from START)
        ▼
┌─────────────────┐     ┌──────────────────────┐
│  Execute Node    │────▶│  Apply state update   │
│  "research"      │     │  via reducers         │
│  (calls function)│     │  (merge partial dict) │
└───────┬─────────┘     └──────────┬───────────┘
        │                          │
        │    ┌─────────────────────┘
        ▼    ▼
┌─────────────────┐
│  Save checkpoint │◄─── If checkpointer attached
│  (snapshot state)│
└───────┬─────────┘
        │
        ▼
┌─────────────────┐     ┌─────────────────┐
│  Evaluate edges  │────▶│  Fixed edge?     │── YES ──▶ Next node
│  from this node  │     │  Conditional?    │── EVAL ──▶ Router fn
└─────────────────┘     │  END?            │── DONE ──▶ Return state
                        └─────────────────┘
```

**The Super-Step Model:**

LangGraph processes nodes in **super-steps**:
1. Pick all nodes ready to execute (have satisfied incoming edges)
2. Execute them (potentially in parallel if independent)
3. Apply all state updates via reducers
4. Save checkpoint
5. Evaluate outgoing edges to determine next super-step
6. Repeat until reaching END

```python
# You can SEE super-steps via streaming:
for step in graph.stream({"topic": "AI"}, stream_mode="updates"):
    print(f"Step: {step}")
    # Output shows which node ran and what state it produced

# stream_mode options:
# "values"  → Full state after each step
# "updates" → Only the changes from each node
# "debug"   → Maximum detail (includes timing, checkpoints)
```

---

## Checkpointing: The Persistence Layer

**What:** Automatic snapshots of graph state saved after every node execution.  
**Why:** Enables conversation memory, crash recovery, time-travel debugging, and human-in-the-loop.

```python
# === In-Memory (development only) ===
from langgraph.checkpoint.memory import MemorySaver
# What: Stores checkpoints in RAM | Why: Fast, zero setup, development only
# ⚠️ WARNING: Lost on restart — never use in production

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

# Must provide thread_id to track separate conversations
config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke({"messages": [("user", "Hello")]}, config=config)

# Second call REMEMBERS the first (same thread_id)
result = graph.invoke({"messages": [("user", "What did I say?")]}, config=config)
# The graph has full conversation history!


# === PostgreSQL (production) ===
# Install: pip install langgraph-checkpoint-postgres
from langgraph.checkpoint.postgres import PostgresSaver

# Connection string to your Postgres database
DB_URI = "postgresql://user:pass@localhost:5432/langgraph_db"

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()  # Creates required tables (run once)
    graph = builder.compile(checkpointer=checkpointer)
    # Now state survives restarts, crashes, and deployments
```

**Checkpoint Mental Model:**

```
Thread "user-123" checkpoints:
┌──────────┬─────────────┬───────────────────┐
│ Step     │ Node        │ State Snapshot     │
├──────────┼─────────────┼───────────────────┤
│ 0        │ START       │ {messages: []}     │
│ 1        │ chatbot     │ {messages: [H,A]}  │
│ 2        │ tool_call   │ {messages: [H,A,T]}│  ◄── time-travel here
│ 3        │ chatbot     │ {messages: [H,A,T,A2]}│
└──────────┴─────────────┴───────────────────┘

You can "rewind" to any checkpoint and re-execute from there.
This is called TIME-TRAVEL DEBUGGING.
```

---

## Human-in-the-Loop (HITL)

**What:** Pausing graph execution to get human approval before continuing.  
**Why:** Critical for production systems — you don't want an AI agent sending emails or modifying databases without human approval.

```python
from langgraph.types import interrupt, Command

def risky_action(state):
    """Node that requires human approval before executing."""

    # This PAUSES the graph and returns control to the caller
    approval = interrupt(
        {
            "question": "Should I send this email?",
            "draft": state["email_draft"],
        }
    )

    # Execution resumes here AFTER human responds
    if approval == "yes":
        send_email(state["email_draft"])
        return {"status": "sent"}
    return {"status": "cancelled"}


# Build graph with checkpointer (required for HITL)
graph = builder.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["risky_action"],  # Pause BEFORE this node
    # interrupt_after=["review"],       # Or pause AFTER a node
)

# First invoke: runs until interrupt point
result = graph.invoke(input, config)
# Graph is now PAUSED — state saved to checkpoint

# Human reviews and resumes:
result = graph.invoke(
    Command(resume="yes"),  # Human approves
    config
)
# Graph continues from where it paused
```

---

## Graph Visualization

LangGraph can render your graph as a Mermaid diagram — invaluable for debugging:

```python
# Generate a Mermaid diagram of your graph
print(graph.get_graph().draw_mermaid())

# Or save as PNG (requires graphviz)
graph.get_graph().draw_mermaid_png(output_file_path="graph.png")
```

**Example output for our research pipeline:**
```mermaid
graph TD
    __start__([START]) --> research
    research --> evaluate
    evaluate -->|quality >= 0.6| write_report
    evaluate -->|quality < 0.6| research
    write_report --> __end__([END])
```

---

## Best Practices

**✅ DO:**
- Always use a checkpointer in production — Why: Enables recovery, memory, and HITL
- Use `stream()` during development — Why: See each node's execution in real-time
- Visualize your graph with `draw_mermaid()` — Why: Catch structural bugs visually
- Use `thread_id` for multi-user/multi-conversation — Why: Isolates state per conversation

**❌ DON'T:**
- Use `MemorySaver` in production — Why bad: Data lost on restart | Fix: Use PostgresSaver
- Forget `thread_id` with checkpointers — Why bad: All users share state | Fix: Unique ID per conversation
- Skip the compile step — Why bad: No validation, raw builder isn't runnable | Fix: Always compile

---

## What's Next

**Learned:** ✅ Build vs runtime phases, ✅ Super-step execution model, ✅ Checkpointing & persistence, ✅ Human-in-the-loop, ✅ Graph visualization  
**Next:** Module 03: Practical Implementation — From minimal to advanced production examples  
**Check:** Can you explain what happens at each step when `invoke()` is called? Can you describe when to use `interrupt_before` vs `interrupt_after`?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-05 | Initial creation |
