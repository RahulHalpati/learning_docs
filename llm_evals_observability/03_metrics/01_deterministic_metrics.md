# 03-1 · Deterministic metrics

> **Level:** Intermediate · **Prerequisites:** [02-1 · Building eval sets](../02_datasets/01_building_eval_sets.md)
> **Time:** 50 min · **Verified:** 2026-08-05 (real EvalKit output)

## Why this matters

Deterministic metrics are free, instant, and reproducible — the same input always scores the same. They can't judge nuance, but they catch a huge share of real regressions, and unlike a judge they never need defending as "probably about right". **Start here; escalate only when they genuinely can't answer the question.**

---

## Exact match

```python
def exact_match(prediction: str, reference: str) -> float:
    return float(prediction.strip().lower() == reference.strip().lower())
```

**Output (real run):**
```
'Paris' vs '  paris '  ->  1.0     (normalization handles case/whitespace)
'Paris.' vs 'Paris'    ->  0.0     <- punctuation breaks it
```

Use it for genuinely closed outputs: a classification label, an enum, an extracted ID. **Don't** use it for prose — that `0.0` on a trailing full stop is exactly why.

## Containment

```python
def contains_answer(prediction, reference) -> float:
    return float(reference.strip().lower() in prediction.strip().lower())
```

**Output (real run):**
```
'The capital is Paris' contains 'Paris'  ->  1.0
```

Forgiving of surrounding prose — good when the model explains its answer. Its weakness: it can't tell *"Paris"* from *"It is definitely not Paris"*. Pair it with something else.

---

## Token F1 — the workhorse

Overlap of word sets, balancing precision and recall. Gives **partial credit**, which is what you want for open text:

**Output (real run, reference = "Flask is a Python micro-framework"):**
```
f1  1.0      | Flask is a Python micro-framework          (identical)
f1  0.9091   | Flask is a Python framework                (minor omission)
f1  0.9231   | Flask is a micro-framework for Python      (reworded)
f1  0.1667   | Redis is an in-memory store                (wrong)
```

Notice it handled **reordering** ("micro-framework for Python") almost as well as the exact phrasing, and dropped hard on a wrong answer. That's the behavior a useful metric needs: tolerant of surface variation, sensitive to meaning changes.

**Jaccard** (intersection over union) is the simpler cousin — same ranking, harsher numbers (0.83 vs 0.91). F1 is usually the better default because precision/recall balance handles length differences more gracefully.

> ⚠️ **Token overlap doesn't understand negation or numbers.** *"The server is running"* and *"The server is not running"* score ~0.89 — near-identical, opposite meanings. Likewise `$100` vs `$1000` differ by one character. If negation or exact figures matter in your domain, add an explicit assertion for them; never rely on overlap alone.

---

## Choosing per task

| Task | Metric |
|------|--------|
| Classification / labels | exact match |
| Extraction (id, date, total) | exact match, after normalization |
| Short factual QA | **token F1** + containment |
| Long-form / summaries | judge ([04](../04_llm_as_judge/README.md)) + properties |
| Anything with a format contract | an **assertion** (valid JSON, has citation) |

---

## Normalization is half the metric

Most "wrong" scores come from formatting, not meaning. Before comparing, normalize consistently: lowercase, strip whitespace and punctuation, collapse spaces, and canonicalize domain values (`$1,000.00` → `1000`, `2026-08-05` → a date). EvalKit's `_tokens()` does the basic version:

```python
_WORD = re.compile(r"[a-z0-9]+")
def _tokens(text): return _WORD.findall(text.lower())
```

Whatever you choose, apply the **same** normalization to prediction and reference — asymmetric normalization silently biases every score.

---

## Recap & next

- ✅ Deterministic metrics are free, instant, reproducible — **start here**.
- ✅ Exact match for closed outputs; containment for prose-wrapped answers; **token F1** as the general default.
- ✅ F1 gave partial credit and survived reordering (0.92) while punishing a wrong answer (0.17).
- ✅ Overlap metrics are **blind to negation and numbers** — add assertions where those matter.
- ✅ Normalize both sides identically; most spurious failures are formatting.
- ✅ Self-check: why does *"The server is not running"* score ~0.89 against *"The server is running"*, and what would you add to catch it?

→ Next: **[03-2 · Semantic & task metrics](02_semantic_metrics.md)**

## Exercises

1. Score these against reference `"Gunicorn is a production WSGI server"`: (a) the identical string, (b) `"Use Gunicorn in production"`, (c) `"Never use Gunicorn in production"`. What does (c) reveal?

<details>
<summary>Solution</summary>

(a) 1.0, (b) high partial credit, (c) **also high** — the negation is invisible to token overlap, so a metric-only pipeline would call a dangerously wrong answer "good". This is the concrete case for a judge or an explicit negation assertion.
</details>
