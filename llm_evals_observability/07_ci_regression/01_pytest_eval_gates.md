# 07-1 · Evals as pytest gates

> **Level:** Intermediate → Advanced · **Prerequisites:** [03-1 · Deterministic metrics](../03_metrics/01_deterministic_metrics.md)
> **Time:** 50 min · **Verified:** 2026-08-05 (real EvalKit run — 22 passed)

## Why this matters

An eval you run by hand is a ritual you'll skip when you're busy — which is exactly when regressions ship. Wiring evals into **pytest** turns quality into a merge blocker: the same mechanism that stops broken code stops degraded quality. This is what makes evaluation an engineering practice rather than a research activity.

---

## An eval is just a test

```python
THRESHOLDS = {"f1": 0.70, "faithfulness": 0.80, "context_recall": 0.90, "judge": 0.70}

@pytest.fixture(scope="module")
def report():
    return run_eval("v2")                     # run the dataset ONCE per session

@pytest.mark.parametrize("metric,minimum", sorted(THRESHOLDS.items()))
def test_metric_meets_threshold(report, metric, minimum):
    actual = report.aggregate()[metric]
    assert actual >= minimum, f"{metric} {actual} below threshold {minimum}"
```

Two deliberate choices:

- **`scope="module"`** — the eval runs once and every test reads the same report. With a real LLM this is the difference between one paid run and one per assertion.
- **`parametrize`** — each metric is its own test with its own name, so a failure says `test_metric_meets_threshold[f1-0.7]` rather than "something was below threshold".

**Output (real run):**
```
......................                                                   [100%]
22 passed in 0.04s
```

---

## Gate on cost too

```python
MAX_COST_USD = 0.01

def test_cost_within_budget(report):
    assert report.total_cost_usd <= MAX_COST_USD
```

Quality gates alone let a "better" prompt triple your bill. This catches prompt bloat at review time, before it multiplies by production traffic ([06-2](../06_tracing_observability/02_cost_latency_tokens.md)).

---

## Gate on specific behaviors

Aggregate scores hide individual disasters. Pin the behaviors you *must* keep:

```python
def test_out_of_scope_question_is_refused(report):
    """The system must say 'I don't know' rather than invent an answer."""
    case = next(c for c in report.cases if c.id == "q6")
    assert "don't know" in case.answer.lower()
```

Every past incident should become one of these. An average can absorb one catastrophic case; a named test cannot.

---

## Test the gate itself

The most important test in the suite:

```python
def test_known_regression_is_detected():
    """Meta-test: prove the gate actually catches a worse version."""
    good, bad = run_eval("v2"), run_eval("v1")
    diff = compare(good, bad)
    assert diff["f1"]["regressed"], "the gate failed to notice a real regression"
    assert diff["judge"]["delta"] < 0
```

> ⚠️ **A quality gate you've never seen fail is a gate you can't trust.** It's easy to write thresholds so loose that nothing ever trips them, then feel protected. This meta-test keeps a *known-bad* version around and asserts the gate catches it — so the suite proves its own sensitivity on every run. If someone weakens the metrics, this test goes red.

---

## Test your eval code

`tests/test_components.py` unit-tests the metrics, judge, tracer, and guardrails themselves:

```python
def test_f1_gives_partial_credit():
    full = metrics.f1_overlap("Flask is a Python micro-framework", "...same...")
    partial = metrics.f1_overlap("Flask is a framework", "Flask is a Python micro-framework")
    none = metrics.f1_overlap("Redis caching", "Flask is a Python micro-framework")
    assert full == 1.0 and 0 < partial < full and none == 0.0
```

A silently broken metric is worse than no metric — you'll trust the number and act on it. Eval code is code; it gets tests.

---

## In CI

```yaml
name: evals
on: [push, pull_request]
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -r requirements.txt
      - name: Run eval gates
        run: pytest -q                            # fails the build if quality regressed
      - name: Publish scorecard
        if: always()
        run: python -m evalkit.report >> $GITHUB_STEP_SUMMARY
```

`if: always()` publishes the scorecard **even when the gate fails** — the reviewer sees which metric moved and by how much, right in the PR summary. That turns a red build into a useful conversation instead of a mystery.

> **Tip — running real-LLM evals in CI.** They cost money and are non-deterministic, so: use a **small sampled subset** on every PR and the **full suite** nightly or on release; cache judge verdicts; and put API keys in repository secrets. Fast, cheap signal on every push; thorough signal on a schedule.

---

## Recap & next

- ✅ Evals as pytest tests = quality becomes a **merge blocker**.
- ✅ `scope="module"` runs the dataset once; `parametrize` names each metric's failure.
- ✅ Gate on **cost** and on **specific behaviors**, not just averages.
- ✅ **Meta-test the gate** with a known-bad version — a gate that never fails is untrustworthy.
- ✅ Unit-test your eval code; publish the scorecard to the PR with `if: always()`.
- ✅ Self-check: why keep a deliberately worse version of the app around in your test suite?

→ Next: **[07-2 · Thresholds & regression detection](02_regression_and_thresholds.md)**

## Exercises

1. Raise `THRESHOLDS["f1"]` to 0.90 and run `pytest -q`. Read the failure message — does it tell you enough to act?

<details>
<summary>Solution</summary>

It fails with `f1 0.7513 below threshold 0.9` — metric, actual, expected. That's a good failure message: actionable without opening the code. Compare it to a bare `assert report.aggregate()["f1"] >= 0.9`, which just says `assert False`. Failure-message quality is what makes a gate usable at 5pm on a Friday.
</details>
