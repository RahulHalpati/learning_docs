# Section 05 · RAG evaluation

> **Prerequisites:** [04 · LLM-as-judge](../04_llm_as_judge/README.md) · **Time:** ~2 h

RAG has two failure modes and you must measure them separately: **retrieval** brought back the wrong documents, or **generation** ignored//invented beyond the right ones. A single end-to-end score can't tell you which — so it can't tell you what to fix.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 05-1 | [Retrieval metrics](01_retrieval_metrics.md) | Did we fetch the right context? |
| 05-2 | [Faithfulness & generation](02_generation_faithfulness.md) | Did the answer stick to that context? |

## What you'll be able to do after this section

- Measure retrieval with precision, recall, and hit-rate@k.
- Measure grounding with faithfulness — and know exactly what it misses.
- Diagnose *which half* of a RAG pipeline is broken.

→ Start: **[05-1 · Retrieval metrics](01_retrieval_metrics.md)**
