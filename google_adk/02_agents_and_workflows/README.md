# Section 02 · Agents & workflows

> **Prerequisites:** [01 · Foundations](../01_foundations/README.md) · **Time:** ~2 h

The heart of ADK: the reasoning agent (`LlmAgent`) and the four orchestration agents that compose it — `Sequential`, `Parallel`, `Loop`, and your own `BaseAgent`.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 02-1 | [LlmAgent](01_llm_agent.md) | How do I configure the reasoning agent — instruction, output, schema? |
| 02-2 | [SequentialAgent](02_sequential_agent.md) | How do I run agents in order and pass results between them? |
| 02-3 | [ParallelAgent](03_parallel_agent.md) | How do I run agents concurrently and gather their outputs? |
| 02-4 | [LoopAgent](04_loop_agent.md) | How do I repeat until good enough, and stop cleanly? |
| 02-5 | [Custom agents](05_custom_agents.md) | How do I write my own orchestration/logic with `BaseAgent`? |

## What you'll be able to do after this section

- Configure `LlmAgent`s (instruction, `output_key`, input/output schemas).
- Compose deterministic pipelines with `Sequential`/`Parallel`/`Loop`.
- Escalate to end a loop; write a custom `BaseAgent` for logic ADK doesn't ship.

→ Start: **[02-1 · LlmAgent](01_llm_agent.md)**
