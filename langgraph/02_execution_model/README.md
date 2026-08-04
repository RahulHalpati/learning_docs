# Section 02 · Execution model

> **Prerequisites:** [01 · Foundations](../01_foundations/README.md) · **Time:** ~90 min

You can build graphs without knowing how they run — but you can't *debug* or *harden* them without it. This section opens the hood: the build-vs-runtime split, the super-step execution model, the several ways to **stream** output, and the production dials for **durability, retries, caching, recursion limits, and runtime configuration**.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 02-1 | [Super-step model](01_super_step_model.md) | What does `compile()` check, and how does `invoke()` actually execute nodes? |
| 02-2 | [Streaming](02_streaming.md) | How do I stream state, updates, tokens, and my own custom events? |
| 02-3 | [Durability, retries & caching](03_durability_retries_caching.md) | How do I retry flaky nodes, cache expensive ones, and bound runaway loops? |
| 02-4 | [Runtime configuration](04_runtime_config.md) | How do I pass per-run settings (user, model, tone) into nodes? |

## What you'll be able to do after this section

- Explain build-time validation and the super-step (BSP) runtime, and visualize a graph.
- Choose the right `stream_mode` (`values`/`updates`/`messages`/`custom`/`debug`) and combine several.
- Add `RetryPolicy`, `CachePolicy`, and `recursion_limit`; understand durability modes.
- Pass typed runtime context to nodes with `context_schema` (and know when to use `configurable`).

→ Start: **[02-1 · Super-step model](01_super_step_model.md)**
