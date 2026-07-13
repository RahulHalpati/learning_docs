# Section 04 · Advanced RAG

> **Prerequisites:** [Section 03 · RAG fundamentals](../03_rag_fundamentals/README.md).
> **Time:** ~6–9 hours.

You have a working RAG system. This section makes it *good*: retrieval that combines keyword and semantic search, a RAG chatbot that remembers the conversation, ways to **measure** whether your answers are actually correct, and what it takes to **serve** RAG as a real application. These are the topics that separate a demo from something you'd put in front of users — kept beginner-friendly, with the heavier production tools clearly marked as optional.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [Better retrieval](01_better_retrieval.md) | How do I combine keyword + semantic search (hybrid)? |
| 02 | [Conversational RAG](02_conversational_rag.md) | How does my RAG bot handle follow-up questions? |
| 03 | [Evaluating RAG](03_evaluating_rag.md) | How do I know if my answers are any good? |
| 04 | [Serving & production](04_serving_and_production.md) | How do I turn this into an app, safely and affordably? |

## What you'll be able to do after this section

- Combine BM25 keyword search with semantic search using an `EnsembleRetriever`.
- Build a conversational RAG chain that uses chat history.
- Evaluate RAG quality manually and understand what automated tools (RAGAS) measure.
- Serve RAG behind an API, and apply the key production concerns: caching, cost, security, monitoring.

→ Start: **[01 · Better retrieval](01_better_retrieval.md)**
