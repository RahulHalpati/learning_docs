# 03-2 · Semantic & task metrics

> **Level:** Intermediate · **Prerequisites:** [03-1 · Deterministic metrics](01_deterministic_metrics.md)
> **Time:** 40 min · **Verified:** 2026-08-05 (concepts; EvalKit metrics verified)

## Why this matters

Token overlap fails on the case that matters most: two answers that share no words but mean the same thing. *"Flask is a lightweight web toolkit"* vs *"Flask is a Python micro-framework"* scores badly on F1 and is basically correct. **Semantic** metrics fix that — at the cost of determinism, speed, and explainability.

---

## Embedding similarity

Encode both texts as vectors, measure the angle between them:

```python
# conceptual — needs an embedding model (sentence-transformers, or an API)
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")     # small, local, no API key

def semantic_similarity(prediction: str, reference: str) -> float:
    a, b = model.encode([prediction, reference])
    return float(util.cos_sim(a, b))                 # ~ -1..1, usually 0..1 in practice
```

Typical behavior: paraphrases land ~0.8–0.95, related-but-different ~0.4–0.6, unrelated <0.3. You then threshold (e.g. ≥0.75 counts as correct).

> **Why EvalKit doesn't ship this:** an embedding model is a ~90 MB download and makes every run slower and machine-dependent, which would break the course's offline determinism. In your project, add it — it's the natural next metric after F1.

**What it fixes:** paraphrase blindness.
**What it doesn't:** semantic similarity is *not* correctness. *"The server is running"* and *"The server is not running"* are ~0.9 similar — negation defeats embeddings almost as badly as it defeats token overlap.

---

## The metric ladder

Each rung costs more and explains less:

| Rung | Metric | Cost | Deterministic | Catches |
|------|--------|------|:---:|---------|
| 1 | assertions (JSON valid, has citation) | ~0 | ✅ | format breakage |
| 2 | exact match / containment | ~0 | ✅ | closed-output errors |
| 3 | token F1 / Jaccard | ~0 | ✅ | factual drift |
| 4 | embedding similarity | low | ⚠️ mostly | paraphrase-tolerant correctness |
| 5 | **LLM-as-judge** | high | ❌ | nuance, reasoning, style, negation |

> **Tip — climb only as far as you need.** Every rung adds latency, cost, and doubt. A suite that's 80% assertions and F1 with a judge on the handful of genuinely open-ended cases runs in seconds and is easy to defend. A suite that's 100% judge is slow, expensive, non-reproducible, and — when a number moves — impossible to explain.

---

## Task-specific metrics

Generic metrics are a fallback. The best metric usually comes from the task itself:

| Task | Metric that actually means something |
|------|--------------------------------------|
| Classification | accuracy, precision/recall, confusion matrix |
| Extraction | field-level exact match; % of required fields present |
| Summarization | faithfulness + compression ratio + key-fact recall |
| Code generation | **does it run? do its tests pass?** (the ideal: objectively checkable) |
| SQL generation | does the query execute, and match the expected result set? |
| Retrieval | precision / recall / hit-rate@k ([05-1](../05_rag_evaluation/01_retrieval_metrics.md)) |
| Agents | task completion, tool-call correctness, step count |

Notice the pattern: wherever you can make the output **objectively checkable** (run the code, execute the SQL, compare a result set), do that instead of scoring text. It's cheaper *and* more truthful than any similarity metric.

---

## Composite scores: use with care

It's tempting to blend everything into one number:

```python
overall = 0.4 * f1 + 0.3 * faithfulness + 0.3 * judge
```

Convenient for a dashboard, dangerous as a gate — a composite lets one metric's rise mask another's fall. That's precisely the failure from [01-1](../01_foundations/01_why_evals.md), where faithfulness climbed to 1.0 *because* quality dropped.

If you use a composite, **always gate on the individual metrics too** (EvalKit's CI does exactly this — a per-metric threshold plus a per-metric regression check, [07](../07_ci_regression/README.md)).

---

## Recap & next

- ✅ Embedding similarity fixes **paraphrase blindness**; threshold it (~0.75) to get a pass/fail.
- ✅ It's still **not correctness** — negation fools embeddings too.
- ✅ Climb the **metric ladder** (assertions → exact → F1 → embeddings → judge) only as far as needed.
- ✅ Prefer **objectively checkable** task metrics (run the code, execute the SQL) over text similarity.
- ✅ Composites hide regressions — gate on individual metrics.
- ✅ Self-check: for a SQL-generating agent, what's a better metric than comparing query strings?

→ Next: **[04 · LLM-as-judge](../04_llm_as_judge/README.md)**

## Exercises

1. Pick an LLM feature you'd build and design its metric panel: one assertion, one deterministic metric, one semantic-or-judge metric. Justify each.

<details>
<summary>Solution</summary>

Example — a support-ticket summarizer: **assertion** "under 80 words and contains no email address"; **deterministic** key-fact recall (do the ticket's ID and product name appear?); **judge** "does the summary capture the customer's actual problem?" Cheap checks catch format and omission bugs; the judge only handles what genuinely needs reading.
</details>
