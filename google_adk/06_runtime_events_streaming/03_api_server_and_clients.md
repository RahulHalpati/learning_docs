# 06-3 · API server & clients

> **Level:** Intermediate · **Prerequisites:** [06-1 · Runners & events](01_runners_and_events.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0; server commands verified present, HTTP calls need it running)

## Why this matters

To let other programs (a web front end, another service) use your agent, expose it over HTTP. ADK's CLI does this for you — no web-framework code. `adk api_server` serves a REST API; `adk web` adds a chat + trace UI; `adk run` is a terminal chat. Same agent, three front doors.

---

## Project layout the CLIs expect

The `adk` commands discover agents from a directory where each agent is a package exposing a `root_agent`:

```
my_agents/
└── research/
    ├── __init__.py        # from . import agent
    └── agent.py           # defines: root_agent = LlmAgent(...)
```

Then, from the parent directory:

```bash
adk run my_agents/research         # interactive terminal chat
adk web my_agents                  # local web UI (chat + event/trace view) at :8000
adk api_server my_agents           # REST API for the agents
```

(These are the CLI counterparts of the programmatic `Runner` from 06-1 — they build a runner for you.)

---

## The REST API

`adk api_server` exposes endpoints mirroring the session/run model:

| Method + path | Does |
|---------------|------|
| `POST /apps/{app}/users/{uid}/sessions/{sid}` | create a session |
| `POST /run` | run the agent, return the events |
| `POST /run_sse` | run and **stream** events (Server-Sent Events) |
| `GET  /apps/{app}/users/{uid}/sessions/{sid}` | fetch session state/history |

Calling `/run` with `curl`:

```bash
curl -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{
        "app_name": "research", "user_id": "u1", "session_id": "s1",
        "new_message": {"role": "user", "parts": [{"text": "hello"}]}
      }'
```

The response is the list of events the run produced — the same `Event` objects from 06-1, as JSON. `/run_sse` streams them instead, for token-by-token UIs.

> **Note:** the endpoints and CLIs are verified to exist in `google-adk 2.5.0` (`adk api_server --help`); actually *calling* them needs the server running and a model configured. Point the agent at `LiteLlm("ollama_chat/...")` and it serves fully offline.

---

## From Python

Any HTTP client works — no special SDK needed:

```python
import requests
r = requests.post("http://127.0.0.1:8000/run", json={
    "app_name": "research", "user_id": "u1", "session_id": "s1",
    "new_message": {"role": "user", "parts": [{"text": "hello"}]},
})
events = r.json()          # list of event dicts
```

---

## Recap & next

- ✅ `adk run` / `adk web` / `adk api_server` serve an agent package (with a `root_agent`) three ways.
- ✅ The REST API mirrors sessions/runs; `/run` returns events, `/run_sse` streams them.
- ✅ Any HTTP client calls it; point the agent at Ollama to serve offline.
- ✅ Self-check: which endpoint would a token-by-token chat UI use, and why?

→ Next: **[07 · Evaluation & quality](../07_evaluation_and_quality/README.md)**

## Exercises

1. Lay out a `research/` agent package with `root_agent` and start `adk web`; chat with it and inspect the event trace in the UI.

<details>
<summary>Solution</summary>

`research/agent.py` defines `root_agent = LlmAgent(name="research", model=LiteLlm("ollama_chat/qwen2.5:0.5b"), ...)`; `research/__init__.py` has `from . import agent`. Run `adk web .` from the parent dir and open the printed URL.
</details>
