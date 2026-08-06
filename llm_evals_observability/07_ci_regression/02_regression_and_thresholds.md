# 07-2 · Thresholds & regression detection

> **Level:** Advanced · **Prerequisites:** [07-1 · Evals as pytest gates](01_pytest_eval_gates.md)
> **Time:** 50 min · **Verified:** 2026-08-05 (real EvalKit regression run)

## Why this matters

Two questions decide whether your gate is useful: **what number do you gate on**, and **how do you catch a slow slide** that never trips an absolute threshold. Get these wrong and you either block every PR (so people disable the gate) or block nothing (so it was theatre).

---

## Absolute thresholds

```python
THRESHOLDS = {"f1": 0.70, "faithfulness": 0.80, "context_recall": 0.90, "judge": 0.70}
```

Where do those numbers come from? **Your measured baseline, minus a small margin** — not aspiration. Procedure:

1. Run the eval on today's system. Say f1 = 0.75.
2. Set the threshold just below (0.70), leaving room for judge/sampling noise.
3. When you genuinely improve the system, **raise the threshold** — a ratchet.

> ⚠️ **Never lower a threshold to make CI green.** That's the one move that hollows out the entire practice: quality drifts down forever, one "temporary" relaxation at a time, and the gate reports success throughout. If a threshold is wrong, change it in its own commit with a written reason — never bundled into the PR it's blocking.

---

## Relative (regression) gates

Absolute thresholds miss the slow slide: 0.75 → 0.74 → 0.73 never trips a 0.70 floor, and one day you're at 0.69 wondering when it happened. So also gate on the **delta** against a baseline:

```python
MAX_REGRESSION = 0.05

def test_no_regression_against_baseline(report):
    baseline = run_eval("v2")          # in CI: load the stored baseline report
    for metric, diff in compare(baseline, report).items():
        assert diff["delta"] >= -MAX_REGRESSION, f"{metric} regressed by {diff['delta']}"
```

**Output (real run — the gate doing its job):**
```
=== v2 (baseline) -> v1 (candidate) ===
  f1                0.7513 -> 0.5847  delta  -0.1666  REGRESSED
  contains          0.6667 -> 0.5     delta  -0.1667  REGRESSED
  faithfulness      0.8333 -> 1.0     delta   0.1667  ok
  context_recall       1.0 -> 1.0     delta      0.0  ok
  judge               0.75 -> 0.5833  delta  -0.1667  REGRESSED

  3 metric(s) regressed
```

Three metrics dropped ~0.17, well past the 0.05 tolerance → build fails. And note **faithfulness went up** — a composite score would have partly cancelled the drop. **Gate per metric**, always ([03-2](../03_metrics/02_semantic_metrics.md)).

---

## Managing the baseline

The baseline is a stored report (JSON) committed to the repo or fetched from CI artifacts:

```python
report.to_dict()          # -> baselines/v2.json
```

Rules that keep it honest:

- **Update it deliberately**, in its own commit, when quality genuinely improves.
- **Regenerate it** whenever the dataset or judge rubric changes — those change the measuring stick, so old numbers aren't comparable ([02-1](../02_datasets/01_building_eval_sets.md), [04-1](../04_llm_as_judge/01_judge_basics.md)).
- **Store the versions** alongside it (dataset version, prompt version, model, price table). A baseline without provenance is a number you can't reason about.

---

## Noise vs signal

With a real LLM, scores vary run to run. Don't chase noise:

| Technique | Effect |
|-----------|--------|
| **temperature = 0** | removes most generation variance |
| **Larger dataset** | shrinks the standard error of the mean |
| **Run N times, take the median** | robust to outliers |
| **Tolerance ≥ noise** | measure run-to-run spread first, then set `MAX_REGRESSION` above it |

Practical approach: run your suite 5× unchanged, observe the spread (say ±0.02), and set the tolerance meaningfully above it (0.05). A gate tighter than your noise floor fails randomly, and a randomly-failing gate gets ignored — the worst outcome of all.

---

## Slicing: where averages lie

A stable average can hide a collapsed category:

**Output (real run):**
```
  per-tag f1:
    basics         1.0
    data           0.2222
    deploy         0.2857
    infra          1.0
    out-of-scope   1.0
```

Overall f1 is 0.75, but `data` is **0.22**. If a change halved `basics` and doubled `data`, the average might not move at all. For anything you care about, gate on the slice:

```python
def test_critical_category_holds(report):
    assert report.by_tag("f1")["basics"] >= 0.9      # this category must not degrade
```

---

## Recap & next

- ✅ Set thresholds from your **measured baseline minus margin**, then **ratchet upward**.
- ✅ **Never lower a threshold to go green** — change it deliberately, in its own commit.
- ✅ Add a **relative gate** (`delta >= -tolerance`) to catch slow slides absolute floors miss.
- ✅ Gate **per metric** — a composite would have hidden this regression behind rising faithfulness.
- ✅ Measure your **noise floor** before setting tolerance; regenerate baselines when the dataset/rubric changes.
- ✅ **Slice by tag** — the average hid a category at 0.22.
- ✅ Self-check: scores drift 0.75 → 0.74 → 0.73 → 0.72 over four PRs, floor is 0.70. Which gate catches it?

→ Next: **[08 · Guardrails](../08_guardrails/README.md)**

## Exercises

1. Add a per-tag gate asserting `data` ≥ 0.5 and run `pytest -q`. It should fail — is that the gate working, or the threshold being wrong?

<details>
<summary>Solution</summary>

It fails because `data` really is 0.22 — the gate is working and telling you a genuine weakness. The right response is to fix the app or the reference (the q2 reference is arguably too narrow, [01-3](../01_foundations/03_environment_setup.md)), **not** to lower the threshold to 0.2. That judgement call — is this a bad system or a bad test? — is the daily work of running evals.
</details>
