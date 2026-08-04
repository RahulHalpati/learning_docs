# Section 07 · Evaluation & quality

> **Prerequisites:** [04-4 · Callbacks](../04_state_sessions_memory/04_callbacks.md) · **Time:** ~60 min

Shipping an agent means measuring it. ADK has **built-in evaluation** (score responses and tool-use trajectories against expected cases) and, via callbacks, a place to enforce **safety guardrails**.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 07-1 | [Evaluation](01_evaluation.md) | How do I define test cases and score an agent with `adk eval`? |
| 07-2 | [Safety & guardrails](02_safety_and_guardrails.md) | How do I stop an agent from doing unsafe things? |

## What you'll be able to do after this section

- Write eval sets and run `adk eval` (and `AgentEvaluator` in tests).
- Understand response-match vs trajectory (tool-use) scoring.
- Layer guardrails with callbacks and model/tool policies.

→ Start: **[07-1 · Evaluation](01_evaluation.md)**
