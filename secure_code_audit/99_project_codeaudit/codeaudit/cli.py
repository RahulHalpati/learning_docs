"""Command-line entry point.

    # scan a directory (offline, stdlib only)
    python -m codeaudit.cli samples/vulnerable_app

    # machine formats for CI
    python -m codeaudit.cli samples/vulnerable_app --format sarif
    python -m codeaudit.cli samples/vulnerable_app --format json

    # add optional LLM triage (offline fake by default; real with CODEAUDIT_LLM=ollama)
    python -m codeaudit.cli samples/vulnerable_app --explain

    # include a dependency (SCA) scan of a requirements file
    python -m codeaudit.cli samples/vulnerable_app --deps samples/vulnerable_app/requirements.txt
"""

from __future__ import annotations

import argparse
import sys

from .dependencies import check_requirements
from .finding import SEVERITY_ORDER
from .report import render
from .scanner import scan_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codeaudit", description="Audit Python source for common vulnerabilities.")
    parser.add_argument("path", help="file or directory to scan")
    parser.add_argument("--format", choices=["text", "json", "sarif"], default="text")
    parser.add_argument("--min-severity", choices=list(SEVERITY_ORDER), default="info",
                        help="hide findings below this severity")
    parser.add_argument("--deps", metavar="REQUIREMENTS",
                        help="also scan a requirements.txt for known-vulnerable pins")
    parser.add_argument("--explain", action="store_true",
                        help="add one-line LLM triage per finding (see providers.py)")
    parser.add_argument("--exit-zero", action="store_true",
                        help="always exit 0 (default: exit 1 when findings exist)")
    args = parser.parse_args(argv)

    findings = scan_path(args.path)
    if args.deps:
        findings += check_requirements(args.deps)

    cutoff = SEVERITY_ORDER[args.min_severity]
    findings = [f for f in findings if SEVERITY_ORDER.get(f.severity, 9) <= cutoff]
    findings.sort(key=lambda f: f.sort_key())

    if args.explain and args.format == "text":
        from .providers import explain, get_chat_model
        model = get_chat_model()
        print(render(findings, "text"))
        print("\n── LLM triage ──")
        for f in findings:
            print(f"• {f.rule_id} {f.file}:{f.line}\n  {explain(f, model)}")
    else:
        print(render(findings, args.format))

    return 0 if (args.exit_zero or not findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
