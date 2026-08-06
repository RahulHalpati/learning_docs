"""LLM-as-judge — scoring with a model, plus the guardrails that make it trustworthy.

The judge here is deterministic (a rubric over the offline model) so the course
is reproducible. Swapping in a real LLM means changing `_score` only; the
rubric, parsing, and meta-evaluation around it stay identical.
"""
from __future__ import annotations

from dataclasses import dataclass

from evalkit.metrics import f1_overlap

RUBRIC = """You are grading an assistant's answer against a reference.

Score 1-5 using ONLY this scale:
5 - fully correct and complete
4 - correct, minor omission
3 - partially correct
2 - mostly wrong but related
1 - wrong or irrelevant

Return JSON: {"score": <1-5>, "reason": "<one sentence>"}
Judge only factual agreement with the reference. Ignore style, length and tone.
"""


@dataclass
class Verdict:
    score: int          # 1..5
    reason: str

    @property
    def normalized(self) -> float:
        """Map 1-5 onto 0-1 so it averages with the other metrics."""
        return round((self.score - 1) / 4, 4)


def _score(prediction: str, reference: str) -> Verdict:
    """Deterministic stand-in for a real judge call."""
    overlap = f1_overlap(prediction, reference)
    if overlap >= 0.95:
        return Verdict(5, "Matches the reference.")
    if overlap >= 0.70:
        return Verdict(4, "Correct with a minor omission.")
    if overlap >= 0.40:
        return Verdict(3, "Partially correct.")
    if overlap >= 0.15:
        return Verdict(2, "Related but largely incorrect.")
    return Verdict(1, "Incorrect or irrelevant.")


def judge(prediction: str, reference: str) -> Verdict:
    """Score one answer. In production this posts RUBRIC to a judge model."""
    return _score(prediction, reference)


def judge_pairwise(answer_a: str, answer_b: str, reference: str) -> str:
    """Which answer is better? Pairwise is more reliable than absolute scoring.

    Ties are reported explicitly rather than broken arbitrarily.
    """
    a, b = judge(answer_a, reference).score, judge(answer_b, reference).score
    if a == b:
        return "tie"
    return "a" if a > b else "b"


def judge_with_position_swap(answer_a: str, answer_b: str, reference: str) -> str:
    """Run pairwise both ways to cancel position bias.

    Judges (real ones) systematically favour whichever answer came first. If the
    verdict flips when you swap the order, the judge isn't actually deciding on
    merit — report a tie instead of trusting it.
    """
    first = judge_pairwise(answer_a, answer_b, reference)
    second = judge_pairwise(answer_b, answer_a, reference)      # swapped
    flipped = {"a": "b", "b": "a", "tie": "tie"}[second]
    return first if first == flipped else "tie"


def agreement(verdicts: list[int], human_labels: list[int]) -> float:
    """Meta-evaluation: how often does the judge agree with a human?

    A judge you haven't validated is just a vibe. Measure this on a labelled
    sample before trusting judge scores as a quality gate.
    """
    if not verdicts:
        return 0.0
    matches = sum(1 for v, h in zip(verdicts, human_labels) if v == h)
    return round(matches / len(verdicts), 4)
