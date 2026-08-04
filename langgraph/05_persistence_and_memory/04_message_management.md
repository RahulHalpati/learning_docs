# 05-4 · Message management

> **Level:** Intermediate · **Prerequisites:** [01-2 · State & messages](../01_foundations/02_state_and_messages.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (langgraph 1.2.9, langchain-core 1.5.0)

## Why this matters

`add_messages` happily appends forever — but every model has a context window, and long histories cost tokens and latency. Production chatbots must **trim** or **summarize** history to keep it bounded. Two tools do this: `trim_messages` (keep a token/count budget) and `RemoveMessage` (delete specific messages by id).

---

## `trim_messages` — keep a budget

`trim_messages` returns a subset of a message list that fits a budget. With `token_counter=len` you budget by *message count* (simple and deterministic); in production you pass a real token counter.

```python
from langchain_core.messages import HumanMessage, SystemMessage, trim_messages

msgs = [SystemMessage(content="sys")] + [HumanMessage(content=f"h{i}") for i in range(5)]

trimmed = trim_messages(
    msgs,
    max_tokens=3,              # budget (here: 3 "tokens" == 3 messages)
    strategy="last",           # keep the most recent
    token_counter=len,         # count by number of messages
    include_system=True,       # always keep the system prompt
    allow_partial=False,
)
print([(m.type, m.content) for m in trimmed])
```

**Output (real run):**
```
[('system', 'sys'), ('human', 'h3'), ('human', 'h4')]
```

The system prompt is preserved and only the two most recent human turns survive — the older ones (`h0`–`h2`) are dropped to fit the budget.

> **Tip:** Wire this as a `pre_model_hook` on a prebuilt agent (03-3), or as a node right before your LLM node, so *every* turn trims before hitting the model. `strategy="last"` keeps recent context; `include_system=True` stops you from accidentally dropping the instructions.

---

## `RemoveMessage` — delete by id

To *permanently* drop messages from state (not just for one model call), return `RemoveMessage(id=...)` — the `add_messages` reducer interprets it as a deletion:

```python
from langgraph.graph import add_messages
from langchain_core.messages import HumanMessage, AIMessage, RemoveMessage

history = [HumanMessage(content="hi", id="1"), AIMessage(content="hello", id="2")]
pruned = add_messages(history, [RemoveMessage(id="1")])   # drop message "1"
print([(m.type, m.content) for m in pruned])
```

**Output (real run):**
```
[('ai', 'hello')]
```

A common pattern: a node that, once history exceeds N messages, returns `RemoveMessage`s for the oldest ones — durable trimming baked into the graph's state, not just a per-call view.

```python
def prune(state):
    msgs = state["messages"]
    if len(msgs) <= 6:
        return {}
    return {"messages": [RemoveMessage(id=m.id) for m in msgs[:-6]]}   # keep last 6
```

---

## Trim vs remove vs summarize

| Technique | Effect | When |
|-----------|--------|------|
| `trim_messages` | filters the list *for a call* | keep recent context under a token budget |
| `RemoveMessage` | deletes from state permanently | hard-cap stored history |
| summarize | replace old turns with a summary message | preserve gist of long conversations |

Summarization is just: run old messages through the LLM, `RemoveMessage` them, and append one summary `AIMessage` — combining the two tools above.

---

## Recap & next

- ✅ `trim_messages` returns a budget-fitting subset (`strategy="last"`, `include_system=True`).
- ✅ `RemoveMessage(id=...)` through `add_messages` deletes permanently from state.
- ✅ Summarize = trim old turns → remove them → append a summary message.
- ✅ Self-check: which do you use to keep the *stored* history small vs. to shrink just one model call?

→ Next: **[06 · Human-in-the-loop](../06_human_in_the_loop/README.md)**

## Exercises

1. Write a `prune` node that keeps only the last 4 messages using `RemoveMessage`, and confirm state shrinks after several turns.

<details>
<summary>Solution</summary>

See the `prune` snippet above with `msgs[:-4]` / keep-last-4. Add it as a node after your chat node; once history exceeds 4, each turn removes the oldest surplus messages.
</details>
