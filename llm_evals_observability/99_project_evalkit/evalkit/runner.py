"""The eval harness: run a dataset through the app, score it, aggregate, compare.

This is the piece that turns "it seemed fine when I tried it" into a number you
can put a threshold on.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean

from evalkit import metrics
from evalkit.app import answer_question
from evalkit.judge import judge

DATASET = Path(__file__).resolve().parent.parent / "datasets" / "qa.jsonl"


def load_dataset(path: Path | str = DATASET) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


@dataclass
class CaseResult:
    id: str
    question: str
    answer: str
    scores: dict[str, float]
    tokens: int
    cost_usd: float
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalReport:
    version: str
    cases: list[CaseResult]

    def aggregate(self) -> dict[str, float]:
        """Mean of each metric across all cases."""
        names = self.cases[0].scores.keys() if self.cases else []
        return {n: round(mean(c.scores[n] for c in self.cases), 4) for n in names}

    @property
    def total_cost_usd(self) -> float:
        return round(sum(c.cost_usd for c in self.cases), 6)

    @property
    def total_tokens(self) -> int:
        return sum(c.tokens for c in self.cases)

    def by_tag(self, metric: str) -> dict[str, float]:
        """Slice a metric by tag — averages hide which *kind* of input fails."""
        buckets: dict[str, list[float]] = {}
        for c in self.cases:
            for tag in c.tags:
                buckets.setdefault(tag, []).append(c.scores[metric])
        return {tag: round(mean(v), 4) for tag, v in sorted(buckets.items())}

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "aggregate": self.aggregate(),
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "cases": [
                {"id": c.id, "scores": c.scores, "answer": c.answer,
                 "tokens": c.tokens, "cost_usd": c.cost_usd}
                for c in self.cases
            ],
        }


def run_eval(version: str = "v2", path: Path | str = DATASET) -> EvalReport:
    cases: list[CaseResult] = []
    for row in load_dataset(path):
        result = answer_question(row["question"], version=version)
        trace = result["trace"]
        verdict = judge(result["answer"], row["reference"])
        cases.append(CaseResult(
            id=row["id"],
            question=row["question"],
            answer=result["answer"],
            tags=row.get("tags", []),
            tokens=trace.total_tokens,
            cost_usd=trace.total_cost_usd,
            scores={
                "f1": metrics.f1_overlap(result["answer"], row["reference"]),
                "contains": metrics.contains_answer(result["answer"], row["reference"]),
                "faithfulness": metrics.faithfulness(result["answer"], result["context"]),
                "context_recall": metrics.context_recall(result["retrieved"],
                                                         row["relevant_docs"]),
                "judge": verdict.normalized,
            },
        ))
    return EvalReport(version=version, cases=cases)


def compare(baseline: EvalReport, candidate: EvalReport) -> dict[str, dict]:
    """Diff two runs — the regression check you run in CI."""
    base, cand = baseline.aggregate(), candidate.aggregate()
    return {
        name: {
            "baseline": base[name],
            "candidate": cand[name],
            "delta": round(cand[name] - base[name], 4),
            "regressed": cand[name] < base[name],
        }
        for name in base
    }
