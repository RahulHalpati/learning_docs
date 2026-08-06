# Section 08 · Guardrails

> **Prerequisites:** [05 · RAG evaluation](../05_rag_evaluation/README.md) · **Time:** ~1 h

Evals run before you ship. **Guardrails** run on every live request — blocking bad input and unsafe output as it happens. Job postings name them explicitly, and they're the difference between an app that behaves in testing and one that behaves in the wild.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 08-1 | [Input & output guardrails](01_guardrails.md) | How do I protect live traffic in both directions? |

## What you'll be able to do after this section

- Redact PII before it reaches a model, a log, or a trace.
- Screen for prompt injection and oversized input.
- Block ungrounded answers with a faithfulness gate at request time.

→ Start: **[08-1 · Input & output guardrails](01_guardrails.md)**
