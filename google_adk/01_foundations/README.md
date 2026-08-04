# Section 01 · Foundations

> **Prerequisites:** [00 · Introduction](../00_introduction.md) · **Time:** ~90 min

The ADK mental model, a bridge from LangGraph, the offline environment, and your first agent built up properly.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 01-1 | [Architecture & primitives](01_architecture_and_primitives.md) | What are agents, runners, sessions, events, and services — and how do they fit? |
| 01-2 | [LangGraph vs ADK](02_langgraph_vs_adk.md) | If I know LangGraph, how do the concepts map onto ADK? |
| 01-3 | [Environment & offline models](03_environment_and_offline_models.md) | How do I run ADK with no API key — Ollama and a fake model? |
| 01-4 | [Your first agent](04_your_first_agent.md) | How do I build, run, and inspect a single `LlmAgent`? |

## What you'll be able to do after this section

- Name ADK's core objects and how a request flows through them.
- Translate LangGraph concepts to ADK (and know when the mental models differ).
- Configure offline models: `LiteLlm` → Ollama for real generation, a fake `BaseLlm` for tests.
- Build and run an `LlmAgent`, and read its events and session state.

→ Start: **[01-1 · Architecture & primitives](01_architecture_and_primitives.md)**
