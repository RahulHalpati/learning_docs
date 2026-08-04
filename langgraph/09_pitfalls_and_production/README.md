# Section 09 · Pitfalls & production

> **Prerequisites:** Sections [01](../01_foundations/README.md)–[08](../08_real_world/README.md) · **Time:** ~90 min

The gap between "works in a notebook" and "works in production" is where projects die. This section is that bridge: the mistakes everyone makes (and their fixes), the performance patterns that keep graphs fast, and the observability you need to trust one in production.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 09-1 | [Pitfalls & best practices](01_pitfalls_best_practices.md) | What are the six mistakes that bite every LangGraph beginner? |
| 09-2 | [Performance & hardening](02_performance_and_hardening.md) | How do I keep graphs fast and make them production-safe? |
| 09-3 | [Observability (LangSmith)](03_observability_langsmith.md) | How do I see what my graph actually did in production? |

## What you'll be able to do after this section

- Recognize and fix the untyped-state, missing-reducer, unbounded-loop, and thread-id mistakes.
- Keep state small, parallelize independent work, and go async for I/O.
- Validate inputs, handle errors, and enable tracing.

→ Start: **[09-1 · Pitfalls & best practices](01_pitfalls_best_practices.md)**
