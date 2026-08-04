# 04-1 · Sessions & state

> **Level:** Beginner · **Prerequisites:** [02-2 · SequentialAgent](../02_agents_and_workflows/02_sequential_agent.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

A **session** is one conversation. It holds two things: the **event history** (what happened) and the **state** (a dict agents read and write). State is how agents pass data to each other and how an agent remembers within a conversation. Understanding its scopes — session vs user vs app vs temporary — is key to building anything stateful.

---

## The SessionService

Sessions are created and stored by a `SessionService`. `InMemorySessionService` is the offline one; there are database- and Vertex-backed versions for production. `InMemoryRunner` bundles an in-memory one for you; to wire services explicitly, use `Runner`:

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()
session = await session_service.create_session(app_name="app", user_id="u", session_id="s1")
runner = Runner(agent=agent, app_name="app", session_service=session_service)
```

Same `app_name` + `user_id` + `session_id` → the same conversation, with its accumulated state and events.

---

## Reading & writing state

Agents write state most often via `output_key` ([02-1](../02_agents_and_workflows/01_llm_agent.md)); tools and custom agents write it directly:

```python
# in a tool:      tool_context.state["key"] = value
# in a custom agent:  ctx.session.state["key"] = value
# after a run:    (await session_service.get_session(...)).state   # inspect it
```

You saw this in the sequential pipeline: `researcher` wrote `state["research"]`, `writer` read it via `{research}`. State is the shared blackboard.

---

## State scopes (prefixes)

A state key's **prefix** controls how long it lives and how widely it's shared:

| Prefix | Scope | Lives as long as | Example |
|--------|-------|------------------|---------|
| *(none)* | this **session** | the conversation | `draft`, `research` |
| `user:` | this **user**, across their sessions | the user | `user:preferred_language` |
| `app:` | the whole **app**, all users | the app | `app:pricing_table` |
| `temp:` | this **turn** only | one invocation | `temp:scratch` |

```python
ctx.session.state["draft"] = "..."               # session-scoped
ctx.session.state["user:name"] = "Ada"           # follows the user across sessions
ctx.session.state["temp:parsed"] = {...}         # discarded after this turn
```

So "remember this user likes espresso" uses `user:`; "scratch value I only need this turn" uses `temp:`. Choosing the right prefix is how you avoid leaking one user's data into another's, or bloating a session with throwaway values.

> **Tip:** `user:` and `app:` state need a *persistent* SessionService to actually outlive a process — with `InMemorySessionService` they vanish on restart, like everything in memory. The prefixes still scope *sharing* correctly in memory; persistence is the production upgrade.

---

## Recap & next

- ✅ A session = event history + a state dict, managed by a `SessionService`.
- ✅ Agents share data through state (`output_key` / `{key}` / direct writes).
- ✅ Prefixes scope state: none = session, `user:` = per user, `app:` = global, `temp:` = one turn.
- ✅ Self-check: which prefix would you use for a user's preferred language vs a one-turn scratch value?

→ Next: **[04-2 · Memory service](02_memory_service.md)**

## Exercises

1. In a tool, set `state["user:visits"]` to an incrementing count and confirm it's readable on the next turn of the same user.

<details>
<summary>Solution</summary>

```python
def track(tool_context) -> dict:
    n = tool_context.state.get("user:visits", 0) + 1
    tool_context.state["user:visits"] = n
    return {"visits": n}
```
With a persistent SessionService this survives across the user's sessions; in memory it survives within the process.
</details>
