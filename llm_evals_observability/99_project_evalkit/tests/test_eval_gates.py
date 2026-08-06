"""The CI quality gate: evals as pytest tests.

This is what turns evaluation from a notebook ritual into a merge blocker.
Run with `pytest -q`; a PR that drops quality below threshold fails the build.
"""
import pytest

from evalkit.runner import compare, run_eval

# Thresholds are a product decision, not a technical one. Set them from your
# current measured baseline, then ratchet upward — never downward to go green.
THRESHOLDS = {
    "f1": 0.70,
    "faithfulness": 0.80,
    "context_recall": 0.90,
    "judge": 0.70,
}
MAX_COST_USD = 0.01          # per full eval run
MAX_REGRESSION = 0.05        # a metric may not drop more than this vs baseline


@pytest.fixture(scope="module")
def report():
    return run_eval("v2")


@pytest.mark.parametrize("metric,minimum", sorted(THRESHOLDS.items()))
def test_metric_meets_threshold(report, metric, minimum):
    actual = report.aggregate()[metric]
    assert actual >= minimum, f"{metric} {actual} below threshold {minimum}"


def test_cost_within_budget(report):
    assert report.total_cost_usd <= MAX_COST_USD


def test_no_regression_against_baseline(report):
    """The candidate must not be meaningfully worse than the baseline."""
    baseline = run_eval("v2")          # in CI: load the stored baseline report
    for metric, diff in compare(baseline, report).items():
        assert diff["delta"] >= -MAX_REGRESSION, f"{metric} regressed by {diff['delta']}"


def test_known_regression_is_detected():
    """Meta-test: prove the gate actually catches a worse version.

    A quality gate you've never seen fail is a gate you can't trust.
    """
    good, bad = run_eval("v2"), run_eval("v1")
    diff = compare(good, bad)
    assert diff["f1"]["regressed"], "the gate failed to notice a real regression"
    assert diff["judge"]["delta"] < 0


def test_out_of_scope_question_is_refused(report):
    """The system must say 'I don't know' rather than invent an answer."""
    case = next(c for c in report.cases if c.id == "q6")
    assert "don't know" in case.answer.lower()


def test_every_case_scored(report):
    assert len(report.cases) == 6
    assert all(set(c.scores) == set(THRESHOLDS) | {"contains"} for c in report.cases)
