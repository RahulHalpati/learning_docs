# 01-2 · State & messages

> **Level:** Beginner · **Prerequisites:** [01-1 · Core concepts](01_core_concepts.md)
> **Time:** 30 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langchain-core 1.5.0)

## Why this matters

The single most common state shape in LangGraph is *a list of chat messages*. Conversations, tool calls, and agent handoffs are all expressed as messages. LangGraph ships a ready-made state (`MessagesState`) and a purpose-built reducer (`add_messages`) for exactly this — and knowing how they behave (append, and **replace-by-id**) unlocks editing and trimming history later.

---

## `MessagesState` — batteries included

`MessagesState` is a `TypedDict` with one field, already wired with the `add_messages` reducer:

```python
# Conceptually, MessagesState IS this:
from typing import Annotated
from typing import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

You can use it directly, or subclass it to add your own fields:

```python
from langgraph.graph import MessagesState

class ChatState(MessagesState):     # inherits the `messages` field + reducer
    user_id: str                    # add whatever else you need
    escalated: bool
```

A minimal chatbot node just appends the model's reply:

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def chatbot(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}   # add_messages appends it

g = StateGraph(MessagesState)
g.add_node("chatbot", chatbot)
g.add_edge(START, "chatbot"); g.add_edge("chatbot", END)
app = g.compile()

out = app.invoke({"messages": [HumanMessage(content="hi")]})
print([(m.type, m.content) for m in out["messages"]])
```

**Output (representative — your wording will differ):**
```
[('human', 'hi'), ('ai', 'Hello! How can I assist you today?')]
```

---

## `add_messages`: append **and** replace-by-id

`add_messages` isn't a dumb concatenation. Two behaviors matter:

1. **New id → append.** A message with a fresh id is added to the end.
2. **Existing id → replace.** A message whose id matches one already in the list *overwrites* it. This is how you **edit** history.

And a special message type, `RemoveMessage`, **deletes** by id:

```python
from langgraph.graph import add_messages
from langchain_core.messages import HumanMessage, AIMessage, RemoveMessage

msgs = [HumanMessage(content="hi", id="1"), AIMessage(content="hello", id="2")]

# Edit: same id "2" replaces the AI message
edited = add_messages(msgs, [AIMessage(content="hello there!", id="2")])

# Delete: RemoveMessage drops the message with id "1"
pruned = add_messages(msgs, [RemoveMessage(id="1")])

print("edited:", [(m.content) for m in edited])
print("pruned:", [(m.type) for m in pruned])
```

**Output (real run):**
```
edited: ['hi', 'hello there!']
pruned: ['ai']
```

> **Tip:** You'll use replace-by-id and `RemoveMessage` in [05-4 · Message management](../05_persistence_and_memory/04_message_management.md) to trim long conversations so they fit the context window.

---

## What about `MessageGraph`?

Older tutorials use `MessageGraph` — a graph whose *entire state is a list of messages*. It still imports in 1.x:

```python
from langgraph.graph import MessageGraph   # legacy convenience
```

But it's effectively `StateGraph(MessagesState)` with less flexibility (you can't add sibling fields like `user_id`). **Recommendation:** use `StateGraph` with `MessagesState` (or a subclass). Reach for `MessageGraph` only when reading old code.

| You want… | Use |
|-----------|-----|
| Just a message list, nothing else | `MessageGraph` (legacy) or `StateGraph(MessagesState)` |
| Messages **plus** other fields | `StateGraph(MyState)` where `MyState(MessagesState)` |

---

## `TypedDict` vs Pydantic for state

| | `TypedDict` | Pydantic `BaseModel` |
|---|---|---|
| Speed / simplicity | ✅ lightest | slightly heavier |
| Runtime validation | ❌ none | ✅ validates inputs |
| Default choice | ✅ most graphs | when untrusted input enters the graph |

Use `TypedDict` unless you specifically want validation at the graph boundary (covered in [09 · Pitfalls & production](../09_pitfalls_and_production/README.md)).

---

## Recap & next

- ✅ `MessagesState` = a `TypedDict` with `messages: Annotated[list, add_messages]`; subclass it to add fields.
- ✅ `add_messages` **appends** new ids and **replaces** matching ids; `RemoveMessage` deletes by id.
- ✅ Prefer `StateGraph(MessagesState)` over the legacy `MessageGraph`.
- ✅ Self-check: how would you *edit* the last AI message in place rather than append a new one?

→ Next: **[01-3 · Environment setup](03_environment_setup.md)**

## Exercises

1. Subclass `MessagesState` to add a `turn_count: int` field and a node that increments it each turn.

<details>
<summary>Solution</summary>

```python
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
class S(MessagesState):
    turn_count: int

def chat(state: S) -> dict:
    return {"messages": [llm.invoke(state["messages"])],
            "turn_count": state.get("turn_count", 0) + 1}

g = StateGraph(S); g.add_node("chat", chat)
g.add_edge(START, "chat"); g.add_edge("chat", END)
print(g.compile().invoke({"messages": [HumanMessage(content="hi")], "turn_count": 0})["turn_count"])
# → 1
```
`turn_count` has no reducer, so it's replaced with the new value each turn.
</details>
