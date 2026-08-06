# 01-3 · Environment setup

> **Level:** Intermediate · **Prerequisites:** [01-2 · The eval loop](02_eval_loop_and_types.md)
> **Time:** 30 min · **Verified:** 2026-08-05 (Python 3.10, pytest 9.1.1 — 22 passed)

## Why this matters

Get the harness running now, so every later lesson is something you can execute and modify rather than read. EvalKit is **stdlib-only** — no API key, no network, no bill — which also means every number in this course is reproducible on your machine.

---

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
cd 99_project_evalkit
pip install -r requirements.txt        # just pytest; the harness is stdlib
pytest -q
```

**Output (real run):**
```
......................                                                   [100%]
22 passed in 0.04s
```

Twenty-two tests: the metrics, the judge, the tracer, the guardrails, and the CI gates — in well under a second.

---

## Run an evaluation

```bash
python -m evalkit.report
```

**Output (real run):**
```
=== Eval report · version v2 · 6 cases ===
  f1               0.7513   ███████████████
  contains         0.6667   █████████████
  faithfulness     0.8333   ████████████████
  context_recall   1.0      ████████████████████
  judge            0.75     ███████████████
  tokens           170
  cost (usd)       0.00264

  per-tag f1:
    basics         1.0
    data           0.2222
    deploy         0.2857
    infra          1.0
    out-of-scope   1.0

  weakest cases:
    q2 f1=0.2222  Alembic handles database migrations.
    q3 f1=0.2857  Never use the Flask dev server in production.
```

How to read it:

- **The metric block** is the headline — but never look at one number alone ([01-1](01_why_evals.md)).
- **Per-tag** is where the value is: overall f1 is 0.75, but `data` scores **0.22** and `deploy` **0.29**. The average hid two badly-failing categories. *Always slice.*
- **Weakest cases** point you at concrete failures to inspect — q2 answered "Alembic handles database migrations" when the reference wanted "Flask-Migrate wraps Alembic".
- **Tokens and cost** sit next to quality so trade-offs are visible.

---

## Compare two versions

```bash
python -m evalkit.report --compare v1
```

**Output (real run):**
```
=== v2 (baseline) -> v1 (candidate) ===
  f1                0.7513 -> 0.5847  delta  -0.1666  REGRESSED
  contains          0.6667 -> 0.5     delta  -0.1667  REGRESSED
  faithfulness      0.8333 -> 1.0     delta   0.1667  ok
  context_recall       1.0 -> 1.0     delta      0.0  ok
  judge               0.75 -> 0.5833  delta  -0.1667  REGRESSED

  3 metric(s) regressed
```

This is the report you'd attach to a pull request.

---

## Export a trace

```bash
python -m evalkit.report --trace
```

**Output (real run, `trace.json`):**
```json
{
  "trace_id": "8f399268d560",
  "name": "rag.answer",
  "duration_ms": 0.05,
  "total_tokens": 32,
  "total_cost_usd": 0.00044,
  "spans": [
    { "name": "retrieve", "span_id": "8d2e1650", "parent_id": null,
      "attributes": { "query": "What is Flask?", "version": "v2",
                      "retrieved": ["d1", "d3"] }, "duration_ms": 0.02 }
  ]
}
```

Same shape a real backend ingests: nested spans, attributes, usage, cost ([06](../06_tracing_observability/README.md)).

---

## The layout

```
99_project_evalkit/
├── evalkit/
│   ├── app.py          # the system under test (a tiny offline RAG pipeline)
│   ├── metrics.py      # deterministic + RAG metrics
│   ├── judge.py        # LLM-as-judge, pairwise, bias control
│   ├── tracing.py      # spans, tokens, cost, latency
│   ├── guardrails.py   # PII, injection, groundedness
│   ├── runner.py       # run dataset -> score -> aggregate -> compare
│   └── report.py       # CLI scorecard
├── datasets/qa.jsonl   # the golden dataset (6 cases)
├── tests/              # 22 tests incl. the CI gate
└── .github/workflows/evals.yml
```

> **Tip — where the real model goes.** `app.py` is deliberately a stub so results are deterministic. Swapping in a real LLM means changing `generate()` (and `judge._score()`); **nothing else moves** — the dataset, metrics, tracing, gates, and CI stay exactly as they are. That's the point of keeping the harness independent of the model.

---

## Recap & next

- ✅ EvalKit is stdlib-only and offline: `pytest -q` → **22 passed**.
- ✅ `python -m evalkit.report` prints a scorecard; `--compare` diffs versions; `--trace` exports a trace.
- ✅ **Always read the per-tag slice** — the average hid two failing categories (0.22 and 0.29).
- ✅ Swapping in a real model touches `generate()` only; the harness is model-independent.
- ✅ Self-check: overall f1 is 0.75 and you're asked "is it good?" — what do you look at before answering?

→ Next: **[02 · Datasets](../02_datasets/README.md)**

## Exercises

1. Run `python -m evalkit.report` and open `datasets/qa.jsonl`. For the weakest case (q2), read the reference and the answer — is the *app* wrong, or is the *reference* unfair?

<details>
<summary>Solution</summary>

Arguably both. The app returned "Alembic handles database migrations" (true, from the right document) but the reference wanted "Flask-Migrate wraps Alembic for Flask". Low scores often mean a **bad reference**, not a bad app — which is why you inspect failures instead of just chasing the number. Fixing dataset quality is real eval work ([02-1](../02_datasets/01_building_eval_sets.md)).
</details>
