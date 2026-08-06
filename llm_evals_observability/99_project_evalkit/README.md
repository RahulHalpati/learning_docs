# 99 · Capstone — EvalKit

> **Level:** Intermediate → Advanced · **Prerequisites:** Sections 01–08
> **Time:** the whole course · **Verified:** 2026-08-05 · Python 3.10 · stdlib-only core · pytest 9.1.1

The complete evaluation and observability harness this course builds. It runs **fully offline** — no API key, no network — so every number below is reproducible on your machine.

## What's in it

| Concern | File | Lesson |
|---------|------|--------|
| System under test (offline RAG) | `evalkit/app.py` | [01-3](../01_foundations/03_environment_setup.md) |
| Golden dataset (6 cases, tagged) | `datasets/qa.jsonl` | [02-1](../02_datasets/01_building_eval_sets.md) |
| Deterministic + RAG metrics | `evalkit/metrics.py` | [03-1](../03_metrics/01_deterministic_metrics.md), [05-1](../05_rag_evaluation/01_retrieval_metrics.md) |
| LLM-as-judge, pairwise, bias control | `evalkit/judge.py` | [04](../04_llm_as_judge/README.md) |
| Tracing: spans, tokens, cost, latency | `evalkit/tracing.py` | [06](../06_tracing_observability/README.md) |
| Guardrails: PII, injection, grounding | `evalkit/guardrails.py` | [08](../08_guardrails/README.md) |
| Runner: score, aggregate, compare | `evalkit/runner.py` | [07-2](../07_ci_regression/02_regression_and_thresholds.md) |
| CLI scorecard | `evalkit/report.py` | [01-3](../01_foundations/03_environment_setup.md) |
| CI quality gate (22 tests) | `tests/`, `.github/workflows/evals.yml` | [07](../07_ci_regression/README.md) |

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # just pytest — the harness is stdlib
pytest -q
```

**Output (real run):**
```
......................                                                   [100%]
22 passed in 0.04s
```

## The scorecard

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

Overall f1 looks fine at 0.75 — but `data` is **0.22**. That's why you always slice.

## Regression detection

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

**The lesson of the whole course is in that output:** faithfulness went **up** while the system got **worse**. `v1`'s naive retriever fetched the wrong document and quoted it faithfully. One metric improved; three regressed; the answer was wrong.

Concretely:

**Output (real run):**
```
v2 answer to "Who won the 1998 world cup?":  I don't know.
v1 answer to "Who won the 1998 world cup?":  Flask 3 uses the application factory pattern.
```

…and `v1` was **15× cheaper** ($0.00017 vs $0.00264). Quality, cost, and correctness pull in different directions — you measure all of them or you optimize blind.

## Traces

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

Same shape Langfuse/OpenTelemetry ingest — migrating swaps the tracer class, not your instrumentation ([06-3](../06_tracing_observability/03_langfuse_and_otel.md)).

## Layout

```
99_project_evalkit/
├── evalkit/
│   ├── app.py          # offline RAG pipeline (v1 = naive, v2 = better)
│   ├── metrics.py      # exact/contains/F1/Jaccard + precision/recall/hit-rate/faithfulness
│   ├── judge.py        # rubric, verdicts, pairwise, position-swap, human agreement
│   ├── tracing.py      # Trace/Span, token+cost accounting, JSON export
│   ├── guardrails.py   # PII redaction, injection screen, grounding gate
│   ├── runner.py       # run -> score -> aggregate -> compare
│   └── report.py       # CLI
├── datasets/qa.jsonl   # golden dataset (tagged, incl. out-of-scope)
├── tests/              # 22 tests: components + CI gates + meta-test
└── .github/workflows/evals.yml
```

## Plugging in a real model

`app.py` is a deterministic stub so the course is reproducible. To use a real LLM:

1. Replace `generate()` with your model call; return real token counts.
2. Replace `judge._score()` with a call using `RUBRIC` at temperature 0.
3. Update `PRICES_PER_1K` with your provider's real rates.

**Nothing else changes** — dataset, metrics, tracing, gates, and CI are model-independent by design.

## Make it your portfolio piece

This is the project that answers *"how do you know your AI works?"* in an interview. To make it yours:

- Point it at **your own** agent or RAG app (from the [LangGraph](../../langgraph/), [ADK](../../google_adk/), or [RAG](../../langchain_rag/) courses).
- Swap the judge for a real LLM and **measure its agreement with your own labels** ([04-2](../04_llm_as_judge/02_rubrics_and_bias.md)).
- Send traces to **Langfuse** and screenshot the dashboard.
- Wire the CI gate into a public repo so the badge is visible.
- Write a short README with the numbers: *"caught a 17% quality regression before merge."*

That last line is worth more than any certificate.
