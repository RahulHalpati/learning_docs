# 09-3 · Observability with LangSmith

> **Level:** Intermediate · **Prerequisites:** [09-2 · Performance & hardening](02_performance_and_hardening.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (concepts; LangSmith requires an account/key)

## Why this matters

In production you can't `print` your way through a graph. You need to see, for every run: which nodes fired, how long each took, what state flowed through, and exactly what went into and out of each LLM call. **LangSmith** (from the LangChain team) captures all of that automatically from any LangGraph run.

> This lesson is conceptual — LangSmith is a hosted service needing an API key, so there's no offline output to show. Tracing is the one thing in the course that needs a LangSmith account.

---

## Turn it on

Tracing is enabled by environment variables — **no code changes** to your graph:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=ls-...            # from smith.langchain.com
export LANGSMITH_PROJECT=my-langgraph-app  # groups related runs
```

From then on, every `invoke`/`stream`/`ainvoke` sends a trace to your project. Open it at [smith.langchain.com](https://smith.langchain.com).

---

## What a trace shows

For one run you get a tree:

- **Each node** as a span, with start/end time and duration — so you can spot the slow one.
- **State in/out** of every node — the values that actually flowed, per step.
- **Every LLM call** nested inside its node: the exact prompt, the response, token counts, and cost.
- **Tool calls** with their arguments and results.
- **Errors** attached to the span that raised them.

It's the `stream_mode="debug"` view ([02-2](../02_execution_model/02_streaming.md)), but persisted, searchable, and shareable — the difference between "it's slow somewhere" and "the `retrieve` node's second attempt took 4.2s".

---

## Beyond tracing

LangSmith also does what raw logs can't:

- **Datasets & evals** — save real inputs, run your graph over them, and score outputs (exact match, LLM-as-judge, custom metrics) to catch regressions before shipping.
- **Monitoring** — dashboards for latency, error rate, token spend over time.
- **Feedback** — attach 👍/👎 or human scores to runs to build eval sets from production traffic.

---

## If you can't use LangSmith

LangGraph's built-in tools still give you visibility:

- `stream_mode="updates"`/`"debug"` for per-step execution.
- `get_state_history()` ([05-2](../05_persistence_and_memory/02_time_travel.md)) to inspect any past checkpoint.
- `draw_mermaid()` ([02-1](../02_execution_model/01_super_step_model.md)) to confirm structure.
- Structured logging inside nodes (scrub PII first).

You lose the persisted, cross-run, cost-annotated view — but you can still debug a single run completely offline.

---

## Recap & next

- ✅ LangSmith traces every run automatically — set three env vars, change no code.
- ✅ A trace shows per-node timing, state in/out, and full LLM/tool call detail.
- ✅ It also does datasets, evals, monitoring, and feedback.
- ✅ Offline fallback: `stream(debug)`, `get_state_history`, `draw_mermaid`, structured logs.
- ✅ Self-check: which env var groups your runs, and which authenticates them?

→ Next: **[10 · Platform & deployment](../10_platform_and_deployment/README.md)**

## Exercises

1. Without an API key: run any earlier graph with `stream_mode="debug"` and identify, from the output, which node took the most work. This is the offline analog of a LangSmith trace.

<details>
<summary>Solution</summary>

`for ev in app.stream(inputs, stream_mode="debug"): print(ev)` emits task/checkpoint events with timing metadata; scan for the node with the largest span. In LangSmith the same insight is one glance at the trace tree.
</details>
