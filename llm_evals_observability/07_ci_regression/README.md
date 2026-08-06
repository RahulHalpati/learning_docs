# Section 07 · CI regression gates

> **Prerequisites:** [03 · Metrics](../03_metrics/README.md) · **Time:** ~2 h

The payoff: evals that **block a merge**. An eval you run manually is a ritual; an eval wired into CI is a safety net that works while you sleep.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 07-1 | [Evals as pytest gates](01_pytest_eval_gates.md) | How do I turn scores into a failing build? |
| 07-2 | [Thresholds & regression detection](02_regression_and_thresholds.md) | What number do I gate on, and how do I catch a slow slide? |

## What you'll be able to do after this section

- Write eval gates as pytest tests with per-metric thresholds and a cost budget.
- Compare against a stored baseline and fail on regression.
- Set defensible thresholds and ratchet them upward over time.

→ Start: **[07-1 · Evals as pytest gates](01_pytest_eval_gates.md)**
