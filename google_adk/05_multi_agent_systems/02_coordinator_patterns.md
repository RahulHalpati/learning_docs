# 05-2 · Coordinator patterns

> **Level:** Intermediate · **Prerequisites:** [05-1 · Delegation & transfer](01_delegation_and_transfer.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (concepts, building on 05-1)

## Why this matters

One coordinator + a flat list of specialists works until you have too many. Then you organize: a **dispatcher** that only routes, a **hierarchy** of coordinators-of-coordinators, and a rule for how deep to go. These are the same topologies as LangGraph's supervisor/hierarchical ([langgraph 07](../../langgraph/07_multi_agent/README.md)), expressed with ADK's `sub_agents`.

---

## Pattern 1 — dispatcher (flat)

A single coordinator whose *only* job is routing; specialists do the work. This is 05-1 scaled to several peers:

```python
support = LlmAgent(
    name="support_dispatcher", model=...,
    instruction="Route each request to the right specialist. Do not answer directly.",
    sub_agents=[billing_agent, tech_agent, account_agent],   # each with a clear description
)
```

Keep the dispatcher thin: it decides, specialists execute. Good when you have a handful of clearly-distinct specialists.

---

## Pattern 2 — hierarchy (coordinators of coordinators)

When specialists themselves have sub-specialists, nest coordinators. Because a coordinator is just an `LlmAgent` with `sub_agents`, and a sub-agent can *also* have `sub_agents`, you get a tree:

```python
research_lead = LlmAgent(name="research_lead", model=...,
    description="Handles all research tasks.",
    sub_agents=[web_researcher, academic_researcher])       # a mid-level coordinator

writing_lead = LlmAgent(name="writing_lead", model=...,
    description="Handles all writing tasks.",
    sub_agents=[drafter, editor])

director = LlmAgent(name="director", model=...,
    instruction="Delegate research to research_lead and writing to writing_lead.",
    sub_agents=[research_lead, writing_lead])               # top-level coordinator
```

Requests flow `director → research_lead → web_researcher`, transferring down the tree. This is how you scale past a flat dispatcher without one coordinator juggling twenty specialists.

---

## Pattern 3 — coordinator + shared workers

Sometimes several coordinators need the *same* specialist (e.g. a translator). Rather than duplicate it, expose it as an `AgentTool` ([03-2](../03_tools/02_builtin_and_agent_tools.md)) that any coordinator can call — control stays with the caller, and the worker is reused.

---

## Choosing depth

| Situation | Structure |
|-----------|-----------|
| 2–5 distinct specialists | flat dispatcher |
| specialists group into domains | one hierarchy level (leads) |
| a worker is needed by many coordinators | expose it as an `AgentTool` |
| deeper than ~3 levels | reconsider — usually a sign of over-decomposition |

Don't add hierarchy for its own sake; each level is another routing decision the models can get wrong.

---

## Recap & next

- ✅ Dispatcher = one thin router over peer specialists.
- ✅ Hierarchy = coordinators with sub-coordinators (a tree), since any `LlmAgent` can have `sub_agents`.
- ✅ Share a worker across coordinators via `AgentTool` instead of duplicating it.
- ✅ Self-check: when do you nest coordinators vs keep a flat dispatcher?

→ Next: **[05-3 · Combining workflow & LLM agents](03_combining_workflow_and_llm.md)**

## Exercises

1. Sketch a two-level hierarchy for a customer-service bot: a top coordinator over `billing_lead` and `tech_lead`, each with two specialists.

<details>
<summary>Solution</summary>

`billing_lead` with `sub_agents=[invoices_agent, refunds_agent]`; `tech_lead` with `sub_agents=[login_agent, api_agent]`; a `director` with `sub_agents=[billing_lead, tech_lead]`. Each agent gets a `description` so its parent can route to it.
</details>
