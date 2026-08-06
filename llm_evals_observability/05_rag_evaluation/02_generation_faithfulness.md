# 05-2 · Faithfulness & generation

> **Level:** Intermediate → Advanced · **Prerequisites:** [05-1 · Retrieval metrics](01_retrieval_metrics.md)
> **Time:** 50 min · **Verified:** 2026-08-05 (real EvalKit output)

## Why this matters

**Faithfulness** (a.k.a. groundedness) asks: is every claim in the answer supported by the retrieved context? It's the primary anti-hallucination metric, and the one most worth automating — because a confidently invented fact is the failure mode that destroys user trust fastest.

It's also the metric this course has already shown lying to you, so we'll be precise about what it does and doesn't mean.

---

## Measuring it

EvalKit's version is a deterministic proxy — what fraction of the answer's content words appear in the context:

```python
def faithfulness(answer: str, context: Sequence[str]) -> float:
    answer_tokens = [t for t in _tokens(answer) if len(t) > 3]     # skip stopwords
    if not answer_tokens:
        return 1.0
    context_tokens = {t for doc in context for t in _tokens(doc)}
    supported = sum(1 for t in answer_tokens if t in context_tokens)
    return supported / len(answer_tokens)
```

**Output (real run, context = "Flask is a Python micro-framework."):**
```
"Flask is a Python framework"                ->  1.0     (every word supported)
"Flask was invented by Guido in Amsterdam"   ->  0.25    (mostly invented)
```

The invented answer scores 0.25 because *invented*, *Guido*, *Amsterdam* appear nowhere in the context. That's hallucination detection in eight lines.

> **How the real tools do it.** [Ragas](https://docs.ragas.io/) decomposes the answer into individual **claims** with an LLM, then verifies each against the context, returning `supported_claims / total_claims`. Same concept, far better resolution — it understands that *"Flask is not a micro-framework"* is unsupported even though every word appears in the context. Token overlap can't. Use Ragas in production; understand the mechanic here.

---

## The three generation metrics

Faithfulness alone is insufficient. The standard trio:

| Metric | Question | Catches |
|--------|----------|---------|
| **Faithfulness** | is it supported by the context? | hallucination |
| **Answer relevancy** | does it address the *question*? | on-topic waffle, evasion |
| **Answer correctness** | does it match the reference? | being grounded but wrong |

You need all three because each covers the others' blind spot — which the course's own regression demonstrates:

**Output (real run, the v1 regression):**
```
faithfulness      0.8333 -> 1.0     delta   0.1667  ok
f1                0.7513 -> 0.5847  delta  -0.1666  REGRESSED
```

> ⚠️ **Faithfulness measures grounding, not truth.** `v1` retrieved the *wrong* document and quoted it verbatim — perfectly faithful (1.0), completely wrong. A system that answers *"I don't know"* to everything also scores 1.0. **Never gate on faithfulness alone**; pair it with relevancy and correctness, and with the retrieval metrics that reveal *why*.

---

## Refusal is a feature

The correct answer to an unanswerable question is *"I don't know."* EvalKit tests this explicitly:

**Output (real run):**
```
v2 answer: I don't know.                                  ✅
v1 answer: Flask 3 uses the application factory pattern.   ❌ confident nonsense
```

And it's pinned as a test:

```python
def test_out_of_scope_question_is_refused(report):
    case = next(c for c in report.cases if c.id == "q6")
    assert "don't know" in case.answer.lower()
```

Include out-of-scope cases in every RAG dataset. A model that never refuses will hallucinate whenever retrieval comes up empty — and retrieval *will* come up empty in production.

---

## Improving faithfulness

1. **Fix retrieval first** ([05-1](01_retrieval_metrics.md)) — you can't ground an answer in context you didn't fetch.
2. **Instruct explicitly**: *"Answer using ONLY the context below. If the context doesn't contain the answer, say 'I don't know'."*
3. **Require citations** — make the model cite the document id per claim; it's both a quality signal and an assertable property.
4. **Lower the temperature** — creativity is the enemy here.
5. **Add a runtime grounding guard** — block low-faithfulness answers before the user sees them ([08](../08_guardrails/README.md)):

```python
from evalkit.guardrails import check_output_grounded
if not check_output_grounded(answer, context, threshold=0.6):
    answer = "I don't have enough information to answer that."
```

That's the same metric doing double duty: an **offline score** in your eval suite and an **online guard** at request time.

---

## Recap & next

- ✅ **Faithfulness** = fraction of the answer supported by the context; the primary hallucination metric.
- ✅ Real tools (Ragas) verify **claims** with an LLM rather than tokens — better resolution, same idea.
- ✅ Use the trio: faithfulness + **relevancy** + **correctness**; each covers the others' blind spot.
- ✅ **Grounded ≠ true** — quoting the wrong document scores 1.0. Never gate on it alone.
- ✅ **Refusal is correct behavior**; test it explicitly with out-of-scope cases.
- ✅ Self-check: an app that always replies "I don't know" — what does it score on faithfulness, and what does that tell you?

→ Next: **[06 · Tracing & observability](../06_tracing_observability/README.md)**

## Exercises

1. Add a case to the dataset whose reference is `"I don't know."` for a question your corpus can't answer, then check both versions handle it.

<details>
<summary>Solution</summary>

`v2` (stopword-filtered retrieval) returns nothing and refuses; `v1` retrieves a spurious document and answers confidently. One dataset row separates a safe system from an unsafe one — which is why out-of-scope coverage is non-negotiable in RAG evaluation.
</details>
