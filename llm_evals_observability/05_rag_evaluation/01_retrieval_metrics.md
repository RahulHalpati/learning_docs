# 05-1 · Retrieval metrics

> **Level:** Intermediate → Advanced · **Prerequisites:** [03-1 · Deterministic metrics](../03_metrics/01_deterministic_metrics.md)
> **Time:** 50 min · **Verified:** 2026-08-05 (real EvalKit output)

## Why this matters

When a RAG app answers badly, there are only two possible causes: **it retrieved the wrong context**, or **it had the right context and answered badly anyway**. Measuring end-to-end quality alone can't distinguish them — so you can't tell whether to fix your retriever or your prompt. Retrieval metrics isolate the first half.

> **The empirical rule of thumb: most RAG failures are retrieval failures.** Fix retrieval before touching prompts.

---

## The three metrics

Your dataset already declares which documents *should* come back (`relevant_docs`, [02-1](../02_datasets/01_building_eval_sets.md)). That makes retrieval objectively scorable.

### Context precision — "was what we fetched relevant?"

```python
def context_precision(retrieved, relevant) -> float:
    return len([d for d in retrieved if d in relevant]) / len(retrieved)
```

**Output (real run):** `retrieved ['d1','d9'], relevant ['d1'] -> 0.5`

Half the retrieved context was noise. Low precision doesn't just waste tokens — irrelevant context actively **distracts** the model and invites hallucination.

### Context recall — "did we fetch everything we needed?"

```python
def context_recall(retrieved, relevant) -> float:
    return len([d for d in relevant if d in retrieved]) / len(relevant)
```

**Output (real run):** `retrieved ['d1'], relevant ['d1','d3'] -> 0.5`

We missed half the needed context. **Low recall caps your answer quality absolutely** — no prompt can recover information that was never retrieved.

### Hit-rate@k — "did anything useful make the cut?"

```python
def hit_rate_at_k(retrieved, relevant, k=3) -> float:
    return float(any(d in relevant for d in retrieved[:k]))
```

**Output (real run):** `['d9','d1'] relevant ['d1'] k=3 -> 1.0`

The blunt "did retrieval work at all" check. Useful as a coarse gate: hit-rate near 1.0 with poor answers points at generation; hit-rate below ~0.8 means fix retrieval first.

---

## Precision vs recall: the k trade-off

Retrieve more documents and recall rises while precision falls.

| k | Recall | Precision | Effect |
|---|--------|-----------|--------|
| 1 | low | high | misses context → incomplete answers |
| 3–5 | good | good | the usual sweet spot |
| 20 | high | low | noise, cost, and "lost in the middle" |

> ⚠️ **More context is not better.** Beyond a handful of documents you pay more, respond slower, and measurably *lose* accuracy — models attend poorly to the middle of long contexts. Tune `k` by measuring, and consider **reranking**: retrieve 20 candidates, rerank with a cross-encoder, keep the top 3. That's how you get high recall *and* high precision.

---

## The diagnosis table

Run both halves and read them together:

| Retrieval | Faithfulness | Diagnosis | Fix |
|-----------|--------------|-----------|-----|
| low recall | high | right answer impossible — context missing | chunking, embeddings, k, reranking |
| high | low | had the facts, invented anyway | prompt, grounding instruction, model |
| high | high, but wrong answer | context right, reasoning wrong | prompt, stronger model |
| low precision | high | grounded in the *wrong* document | reranking, filtering |

That last row is EvalKit's real regression ([01-1](../01_foundations/01_why_evals.md)): `v1` retrieved an irrelevant document and faithfully quoted it — faithfulness **1.0**, answer wrong. Retrieval metrics are what expose that.

---

## Improving retrieval (in order of payoff)

1. **Chunking** — chunks too large bury the answer; too small lose context. Usually the biggest single lever.
2. **Hybrid search** — combine BM25 keyword search with vector search; each catches what the other misses (exact IDs vs paraphrases).
3. **Reranking** — a cross-encoder over the top-20; the highest-value addition to a working pipeline.
4. **Query rewriting** — expand or clarify the query before searching.
5. **Metadata filtering** — restrict by date, tenant, or document type before ranking.

EvalKit's `v2` improvement was the crudest form of #1's cousin — stopword filtering — and it moved f1 from 0.585 to 0.751.

---

## Recap & next

- ✅ RAG has two halves; measure them **separately** or you can't diagnose failures.
- ✅ **Precision** = was the context relevant; **recall** = did we get it all; **hit-rate@k** = did anything land.
- ✅ Low recall **caps** answer quality; low precision **distracts** the model.
- ✅ Bigger `k` isn't better — retrieve wide, **rerank**, keep few.
- ✅ Use the diagnosis table: retrieval + faithfulness together tell you what to fix.
- ✅ Self-check: recall is 0.4 and faithfulness is 0.95. Do you improve your prompt or your retriever?

→ Next: **[05-2 · Faithfulness & generation](02_generation_faithfulness.md)**

## Exercises

1. In EvalKit, change `retrieve()`'s default `k` from 2 to 4 and re-run `python -m evalkit.report`. What happens to faithfulness and f1, and why?

<details>
<summary>Solution</summary>

More context usually raises recall but adds noise, so faithfulness often drops (more unsupported words available to drift toward) and f1 can move either way. The point isn't which direction it moves — it's that you now **measure** the effect of a tuning decision instead of guessing.
</details>
