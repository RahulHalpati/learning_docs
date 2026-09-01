# 05-3 · Long-term memory (the store)

> **Level:** Intermediate · **Prerequisites:** [05-1 · Checkpointers](01_checkpointers.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9)

## Why this matters

Checkpointers give **short-term** memory: everything within one `thread_id`. But "remember that Alice is vegetarian" should survive *across* conversations — a new thread tomorrow should still know it. That's **long-term** memory, and LangGraph provides it through a separate abstraction: the **store** (`BaseStore`). Threads are episodic; the store is your agent's persistent knowledge.

---

## Namespaces, keys, values

The store is a namespaced key-value document store. A **namespace** is a tuple (e.g. `("users", "alice")`); within it you `put`/`get`/`search` JSON documents by key.

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
ns = ("users", "alice")                     # namespace: this user's memories

store.put(ns, "pref1", {"topic": "coffee", "note": "likes espresso"})
store.put(ns, "pref2", {"topic": "food",   "note": "vegetarian"})

print("get:", store.get(ns, "pref1").value)
print("search:", [(i.key, i.value["note"]) for i in store.search(ns)])
```

**Output (real run):**
```
get: {'topic': 'coffee', 'note': 'likes espresso'}
search: [('pref1', 'likes espresso'), ('pref2', 'vegetarian')]
```

`InMemoryStore` is the dev store; `PostgresStore` is the production one (same API, durable, shared across processes).

---

## Wiring the store into a graph

Compile with `store=...` and any node can accept a `store` parameter to read/write memories — keyed off the runtime config (e.g. the user id):

```python
# app = builder.compile(checkpointer=..., store=InMemoryStore())
#
# def respond(state, *, store):
#     memories = store.search(("users", state["user_id"]))
#     # ... use memories to personalize the reply ...
#     store.put(("users", state["user_id"]), "last_seen", {"ts": ...})
```

The checkpointer and store are independent: one remembers *this* conversation, the other remembers *facts about the user* across all conversations.

---

## Semantic search

Give the store an embedding function and `search(..., query=...)` ranks memories by *meaning*, not exact keys — the foundation of retrieval-augmented memory:

```python
from langgraph.store.memory import InMemoryStore

VOCAB = ["coffee", "espresso", "tea", "food", "vegetarian", "python", "code"]
def embed(texts):                                   # toy offline embedding (bag-of-words)
    return [[float(t.lower().count(w)) for w in VOCAB] for t in texts]

store = InMemoryStore(index={"embed": embed, "dims": len(VOCAB), "fields": ["text"]})
ns = ("memories",)
store.put(ns, "m1", {"text": "loves espresso coffee"})
store.put(ns, "m2", {"text": "vegetarian food only"})
store.put(ns, "m3", {"text": "writes python code daily"})

hits = store.search(ns, query="what coffee do they like", limit=2)
print([(h.key, round(h.score, 3), h.value["text"]) for h in hits])
```

**Output (real run):**
```
[('m1', 0.707, 'loves espresso coffee'), ('m2', 0.0, 'vegetarian food only')]
```

The coffee memory ranks top for a coffee query. In production, swap the toy `embed` for a real embedding model (e.g. an embeddings client) and `PostgresStore` with a vector index.

> **Tip:** `InMemoryStore` falls back to pure-Python vector math and warns if NumPy is missing — fine for learning; `uv pip install numpy` for speed. `index={"fields": [...]}` chooses which document fields get embedded.

---

## Recap & next

- ✅ The **store** is cross-thread long-term memory: `put`/`get`/`search` JSON docs under tuple **namespaces**.
- ✅ Compile with `store=...`; nodes take a `store` param — independent of the checkpointer.
- ✅ Add an `index={"embed": ...}` for **semantic** search by meaning.
- ✅ `InMemoryStore` (dev) → `PostgresStore` (prod).
- ✅ Self-check: which remembers "Alice is vegetarian" across days — the checkpointer or the store?

→ Next: **[05-4 · Message management](04_message_management.md)**

## Exercises

1. Store three "facts" about a user and retrieve the two most relevant to the query "favorite programming language".

<details>
<summary>Solution</summary>

With the toy `embed` above, `store.search(ns, query="favorite programming language", limit=2)` ranks `m3` ("python code") first because the query shares the `python`/`code` vocabulary dimensions.
</details>
