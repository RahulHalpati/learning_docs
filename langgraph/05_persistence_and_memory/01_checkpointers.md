# 05-1 · Checkpointers

> **Level:** Intermediate · **Prerequisites:** [03-1 · Your first chatbot](../03_building_graphs/01_first_chatbot.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langgraph-checkpoint-sqlite 3.1.0)

## Why this matters

A checkpointer saves a snapshot of state after every super-step. That one mechanism gives you *four* features at once: conversation memory, crash recovery, human-in-the-loop pauses, and time-travel. You've used `InMemorySaver`; here's the full family and how to pick.

---

## The `thread_id` model

A checkpointer stores checkpoints under a **thread**. You select the thread with `config["configurable"]["thread_id"]`. Same thread → continues; new thread → fresh state. This is what isolates one user/conversation from another.

```python
config = {"configurable": {"thread_id": "user-123"}}
app.invoke(inputs, config)     # loads + saves thread "user-123"
```

Forget the `thread_id` with a checkpointer attached and you'll get an error — LangGraph won't guess which conversation you mean.

---

## The three checkpointers

| Checkpointer | Import | Storage | Use |
|--------------|--------|---------|-----|
| `InMemorySaver` | `langgraph.checkpoint.memory` | RAM | dev, tests (lost on restart) |
| `SqliteSaver` | `langgraph.checkpoint.sqlite` | a file / `:memory:` | single-node, local durability |
| `PostgresSaver` | `langgraph.checkpoint.postgres` | Postgres | production, multi-node |

`InMemorySaver` you've seen. `SqliteSaver` gives you *durable* memory with zero infrastructure:

```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)  # a real file
checkpointer = SqliteSaver(conn)
# app = builder.compile(checkpointer=checkpointer)
```

State now survives process restarts — reopen the same file, invoke with the same `thread_id`, and the conversation is right where you left it. (Use `":memory:"` instead of a filename for an ephemeral test DB.)

`PostgresSaver` is the production choice; it needs a one-time `.setup()` to create tables:

```python
# uv pip install langgraph-checkpoint-postgres
from langgraph.checkpoint.postgres import PostgresSaver

DB = "postgresql://user:pass@localhost:5432/langgraph"
with PostgresSaver.from_conn_string(DB) as cp:
    cp.setup()                                  # run once, creates tables
    # app = builder.compile(checkpointer=cp)
```

> **Tip:** Async variants exist — `AsyncSqliteSaver`, `AsyncPostgresSaver` — for `ainvoke`/`astream` under load. In production, give `PostgresSaver` a **connection pool** rather than a single connection so concurrent requests don't serialize on one socket.

---

## What one checkpoint holds

Each checkpoint is a snapshot: the full state `values`, the `next` nodes to run, and metadata. That's why the same saver powers memory *and* resume *and* time-travel — they're all just "load a checkpoint and continue". You'll read and edit these snapshots directly in the next lesson.

---

## Recap & next

- ✅ A checkpointer snapshots state per step; `thread_id` selects the conversation.
- ✅ `InMemorySaver` (dev) → `SqliteSaver` (local durable) → `PostgresSaver` (production).
- ✅ Postgres needs `.setup()` once; use async savers + a connection pool at scale.
- ✅ Self-check: which checkpointer would you use for a laptop CLI tool that must remember across runs?

→ Next: **[05-2 · Time-travel](02_time_travel.md)**

## Exercises

1. Swap the chatbot from [03-1](../03_building_graphs/01_first_chatbot.md) to `SqliteSaver` with a real file, run it, restart the script (keep the file), and confirm the history persisted.

<details>
<summary>Solution</summary>

```python
conn = sqlite3.connect("chat.sqlite", check_same_thread=False)
app = builder.compile(checkpointer=SqliteSaver(conn))
# first run: say "My name is Alex"; rerun the script: ask "What's my name?"
# same thread_id → the second process sees the first process's messages.
```
</details>
