# 03-1 · Your first chatbot

> **Level:** Beginner · **Prerequisites:** [01 · Foundations](../01_foundations/README.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langchain-core 1.5.0)

## Why this matters

The "hello world" of agents is a chatbot that **remembers** the conversation. It's the smallest program that needs the two ideas you'll use forever: `MessagesState` (accumulating chat history) and a **checkpointer** keyed by `thread_id` (persisting that history between calls). Get this and you understand short-term memory.

---

## The whole thing

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage
from langchain_core.language_models.fake_chat_models import FakeListChatModel

# Offline model with two scripted turns. Swap for get_model()/ChatOllama for real replies.
llm = FakeListChatModel(responses=["Nice to meet you, Alex!", "You said your name is Alex."])

def chatbot(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}   # add_messages appends

builder = StateGraph(MessagesState)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

app = builder.compile(checkpointer=InMemorySaver())        # ← memory lives here
```

Two things make it a *conversation* rather than isolated one-shots:

1. **`MessagesState`** accumulates messages via the `add_messages` reducer.
2. **`checkpointer=InMemorySaver()`** saves state after each run, and **`thread_id`** says *which* conversation to load.

```python
config = {"configurable": {"thread_id": "demo-1"}}         # names this conversation

app.invoke({"messages": [HumanMessage(content="My name is Alex.")]}, config)
out = app.invoke({"messages": [HumanMessage(content="What's my name?")]}, config)

print("history length:", len(out["messages"]))
for m in out["messages"]:
    print(" ", m.type, "|", m.content)
```

**Output (real run):**
```
history length: 4
  human | My name is Alex.
  ai | Nice to meet you, Alex!
  human | What's my name?
  ai | You said your name is Alex.
```

The second `invoke` only *added* the new question — yet the state has all **four** messages. That's the checkpointer replaying thread `demo-1`'s saved history, then the reducer appending. Use a different `thread_id` and you get a fresh, empty conversation.

> **Tip:** `InMemorySaver` (the name `MemorySaver` is a deprecated alias for it) keeps everything in RAM — perfect for learning and tests, gone on restart. Section 05 swaps in `SqliteSaver`/`PostgresSaver` for durable memory.

---

## Going live

To get real replies, swap the model — nothing else changes:

```python
# from langchain_ollama import ChatOllama
# llm = ChatOllama(model="qwen2.5:0.5b", temperature=0.7)
```

Run with Ollama and turn 2 genuinely answers "Your name is Alex" from the replayed history.

---

## Recap & next

- ✅ `MessagesState` + `add_messages` accumulate chat history.
- ✅ A **checkpointer** + **`thread_id`** turn stateless calls into a remembered conversation.
- ✅ `InMemorySaver` is for dev; durable savers come in Section 05.
- ✅ Self-check: what happens to the history if you change `thread_id` on the second call?

→ Next: **[03-2 · Tools & the ReAct loop](02_tools_and_react.md)**

## Exercises

1. Invoke the chatbot with a **second** `thread_id` after the first conversation and confirm its history starts empty.

<details>
<summary>Solution</summary>

```python
other = {"configurable": {"thread_id": "demo-2"}}
out = app.invoke({"messages": [HumanMessage(content="Hi")]}, other)
print(len(out["messages"]))   # → 2 (just this turn), not 6 — threads are isolated
```
</details>
