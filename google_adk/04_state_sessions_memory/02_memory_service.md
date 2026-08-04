# 04-2 · Memory service

> **Level:** Intermediate · **Prerequisites:** [04-1 · Sessions & state](01_sessions_and_state.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

Session state is scoped to a conversation (or a user's sessions). The **MemoryService** is for *long-term, searchable* knowledge that spans everything — "what did this user tell me last week?". You add finished sessions to memory, then search them by query. It's ADK's counterpart to LangGraph's store ([langgraph 05-3](../../langgraph/05_persistence_and_memory/03_long_term_memory_store.md)).

---

## Add a session to memory, then search

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.genai import types
from fake_model import FakeAdkModel        # lesson 01-3

agent = LlmAgent(name="a", model=FakeAdkModel(model="f", responses=["hello world"]),
                 instruction="x", output_key="out")

async def main():
    sessions = InMemorySessionService()
    memory = InMemoryMemoryService()
    runner = Runner(agent=agent, app_name="app",
                    session_service=sessions, memory_service=memory)

    # 1. run a conversation
    await sessions.create_session(app_name="app", user_id="u", session_id="s1")
    msg = types.Content(role="user", parts=[types.Part(text="hi")])
    async for _ in runner.run_async(user_id="u", session_id="s1", new_message=msg):
        pass

    # 2. archive the finished session into long-term memory
    finished = await sessions.get_session(app_name="app", user_id="u", session_id="s1")
    await memory.add_session_to_memory(finished)

    # 3. later, from any session, search memory
    result = await memory.search_memory(app_name="app", user_id="u", query="hello")
    print("results:", len(result.memories))
    print("text:", result.memories[0].content.parts[0].text)

asyncio.run(main())
```

**Output (real run):**
```
results: 1
text: hello world
```

The conversation was archived, then found again by a query from *outside* that session. That's the long-term/short-term split: **session state** = this conversation; **memory** = a searchable archive across conversations.

---

## Using memory inside an agent

The typical pattern: a tool (or callback) searches memory and injects relevant hits into the prompt — retrieval-augmented memory. ADK also ships a prebuilt `load_memory` / `preload_memory` tool so an agent can query its own memory during a run.

```python
# from google.adk.tools import load_memory
# agent = LlmAgent(name="a", model=..., tools=[load_memory])
# the model can now call load_memory("what did the user say about coffee?")
```

---

## Dev vs production

| Service | Storage | Search |
|---------|---------|--------|
| `InMemoryMemoryService` | RAM | keyword match |
| **Vertex AI Memory Bank** | managed | semantic (embeddings) |

`InMemoryMemoryService` is perfect for learning and tests (what we use). In production, Vertex AI Memory Bank gives durable, semantic recall — same `add_session_to_memory` / `search_memory` API, better retrieval.

---

## Recap & next

- ✅ `MemoryService` = long-term, searchable knowledge across sessions.
- ✅ `add_session_to_memory(session)` archives; `search_memory(query=...)` retrieves.
- ✅ `InMemoryMemoryService` (dev, keyword) → Vertex Memory Bank (prod, semantic).
- ✅ Self-check: what's the difference between putting a fact in `session.state` vs in memory?

→ Next: **[04-3 · Artifacts](03_artifacts.md)**

## Exercises

1. Run two separate sessions for the same user, add both to memory, and search across them.

<details>
<summary>Solution</summary>

Create `s1` and `s2`, run a message through each, `add_session_to_memory` for both, then `search_memory(query=...)` — results span both sessions for that `user_id`.
</details>
