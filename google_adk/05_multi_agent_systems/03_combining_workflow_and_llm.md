# 05-3 · Combining workflow & LLM agents

> **Level:** Intermediate · **Prerequisites:** [02-2 · SequentialAgent](../02_agents_and_workflows/02_sequential_agent.md) · [05-1 · Delegation & transfer](01_delegation_and_transfer.md)
> **Time:** 25 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

ADK's real power is *mixing* deterministic orchestration (`Sequential`/`Parallel`/`Loop`) with LLM-driven decisions (delegation). Use workflow agents where the process is fixed and predictable; use LLM routing where a judgment call is needed. The best systems layer both.

---

## Workflow *contains* LLM agents

The most common shape: a `SequentialAgent` whose steps are `LlmAgent`s (and maybe a `ParallelAgent` or `LoopAgent` in the middle):

```python
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent, LlmAgent

gather = ParallelAgent(name="gather", sub_agents=[web_agent, docs_agent])   # fan-out
refine = LoopAgent(name="refine", sub_agents=[writer, critic], max_iterations=3)  # revise

pipeline = SequentialAgent(name="pipeline", sub_agents=[
    gather,        # 1. gather sources in parallel (LLM agents inside a Parallel)
    refine,        # 2. draft & critique in a loop
    publisher,     # 3. an LlmAgent that finalizes
])
```

The *structure* (gather → refine → publish) is deterministic and readable; the *content* at each step is LLM-driven. You get predictable control flow without hoping one giant prompt orchestrates itself.

---

## LLM agent *delegates into* a workflow

The inverse also works: a coordinator `LlmAgent` can transfer to a sub-agent that happens to be a `SequentialAgent`. So the LLM decides *whether* to run a fixed pipeline:

```python
coordinator = LlmAgent(
    name="coordinator", model=...,
    instruction="If the user wants a report, delegate to the report_pipeline.",
    sub_agents=[report_pipeline, quick_answer_agent],   # report_pipeline is a SequentialAgent
)
```

The LLM makes the judgment ("this needs the full report process"), then a deterministic workflow executes it.

---

## The design rule

| Use a **workflow agent** when… | Use an **LlmAgent** (delegation) when… |
|---|---|
| the order of steps is known ahead of time | the next step depends on understanding the request |
| you want reproducible, testable control flow | you need flexible, judgment-based routing |
| steps are "always do A then B" | it's "figure out who should handle this" |

Deterministic where you can, LLM-driven where you must. Over-using LLM routing makes systems flaky; over-using rigid workflows makes them brittle. Mixing is the craft.

> **Tip:** This is exactly what the [capstone](../99_project_adk_research_assistant/) does — a coordinator delegating to a `SequentialAgent` (research → analyze → write) with a `LoopAgent` reviewer inside. Deterministic pipeline, LLM entry point.

---

## Recap & next

- ✅ Nest `LlmAgent`s inside `Sequential`/`Parallel`/`Loop` for LLM content with deterministic structure.
- ✅ Or let a coordinator `LlmAgent` delegate *into* a workflow agent.
- ✅ Rule: deterministic where the process is fixed, LLM-driven where judgment is needed.
- ✅ Self-check: would "extract → validate → store" be a workflow agent or LLM delegation, and why?

→ Next: **[06 · Runtime, events & streaming](../06_runtime_events_streaming/README.md)**

## Exercises

1. Design a pipeline: fan out two research agents (`ParallelAgent`), then a `SequentialAgent` of writer→editor. Which parts are deterministic, which LLM-driven?

<details>
<summary>Solution</summary>

Structure (parallel gather, then write→edit in order) is deterministic — workflow agents. The *content* each agent produces is LLM-driven. No routing judgment is needed here, so no delegation — a pure workflow composition.
</details>
