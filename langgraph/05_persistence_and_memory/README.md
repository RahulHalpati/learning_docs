# Section 05 · Persistence & memory

> **Prerequisites:** [03-1 · Your first chatbot](../03_building_graphs/01_first_chatbot.md) · **Time:** ~2 h

Memory is what separates a toy from an assistant. This section covers **short-term** memory (checkpointers + threads, and their durable variants), **time-travel** (inspect, replay, and fork past checkpoints), **long-term** memory (the cross-thread store, with semantic search), and keeping conversations inside the context window with **message management**.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 05-1 | [Checkpointers](01_checkpointers.md) | How do I persist state — in memory, SQLite, or Postgres — and isolate threads? |
| 05-2 | [Time-travel](02_time_travel.md) | How do I list past checkpoints, replay from one, and fork by editing state? |
| 05-3 | [Long-term memory (the store)](03_long_term_memory_store.md) | How do I remember facts *across* conversations, and search them semantically? |
| 05-4 | [Message management](04_message_management.md) | How do I trim/delete history so it fits the context window? |

## What you'll be able to do after this section

- Choose and wire `InMemorySaver` / `SqliteSaver` / `PostgresSaver`; isolate users with `thread_id`.
- Use `get_state_history()`, replay from a checkpoint, and `update_state()` to fork/edit.
- Store cross-thread memories in the `BaseStore` and retrieve them with keys or semantic search.
- Trim and delete messages with `trim_messages` and `RemoveMessage`.

→ Start: **[05-1 · Checkpointers](01_checkpointers.md)**
