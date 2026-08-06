"""CLI: run an eval, print a scorecard, optionally compare two versions.

    python -m evalkit.report                 # score the current version
    python -m evalkit.report --compare v1    # regression report vs a candidate
    python -m evalkit.report --trace         # export one trace as JSON
"""
from __future__ import annotations

import argparse

from evalkit.app import answer_question
from evalkit.runner import compare, run_eval


def print_scorecard(report) -> None:
    print(f"\n=== Eval report · version {report.version} · {len(report.cases)} cases ===")
    for name, value in report.aggregate().items():
        bar = "█" * int(value * 20)
        print(f"  {name:<16} {value:<8} {bar}")
    print(f"  {'tokens':<16} {report.total_tokens}")
    print(f"  {'cost (usd)':<16} {report.total_cost_usd}")

    print("\n  per-tag f1:")
    for tag, value in report.by_tag("f1").items():
        print(f"    {tag:<14} {value}")

    weak = sorted(report.cases, key=lambda c: c.scores["f1"])[:3]
    print("\n  weakest cases:")
    for c in weak:
        print(f"    {c.id} f1={c.scores['f1']:<7} {c.answer[:56]}")


def print_comparison(baseline, candidate) -> None:
    print(f"\n=== {baseline.version} (baseline) -> {candidate.version} (candidate) ===")
    regressions = 0
    for name, d in compare(baseline, candidate).items():
        status = "REGRESSED" if d["regressed"] else "ok"
        regressions += d["regressed"]
        print(f"  {name:<16} {d['baseline']:>7} -> {d['candidate']:<7} "
              f"delta {d['delta']:>8}  {status}")
    print(f"\n  {regressions} metric(s) regressed")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v2")
    ap.add_argument("--compare", metavar="VERSION", help="compare against this version")
    ap.add_argument("--trace", action="store_true", help="export one trace to trace.json")
    args = ap.parse_args()

    report = run_eval(args.version)
    print_scorecard(report)

    if args.compare:
        print_comparison(report, run_eval(args.compare))

    if args.trace:
        result = answer_question("What is Flask?", version=args.version)
        path = result["trace"].export("trace.json")
        print(f"\n  trace written to {path}")


if __name__ == "__main__":
    main()
