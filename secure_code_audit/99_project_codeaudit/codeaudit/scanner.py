"""Walk a path, parse every .py file, run all rules + taint, collect Findings."""

from __future__ import annotations

import ast
from pathlib import Path

from .finding import Finding
from .rules import ALL_RULES
from .taint import find_taint


def scan_source(source: str, filename: str = "<string>") -> list[Finding]:
    """Run every rule and the taint analysis over one file's source text."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [Finding("CA000", "info", f"Could not parse file: {exc.msg}",
                        filename, exc.lineno or 0)]

    lines = source.splitlines()
    findings: list[Finding] = []
    for rule_cls in ALL_RULES:
        rule = rule_cls(filename, lines)
        rule.visit(tree)
        findings.extend(rule.findings)
    findings.extend(find_taint(tree, filename, lines))
    return findings


def scan_path(path: str | Path) -> list[Finding]:
    """Scan a single .py file or, recursively, every .py file under a directory."""
    path = Path(path)
    files = [path] if path.is_file() else sorted(path.rglob("*.py"))
    findings: list[Finding] = []
    for file in files:
        if any(part in {".venv", "venv", "__pycache__", ".git"} for part in file.parts):
            continue
        try:
            source = file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        findings.extend(scan_source(source, str(file)))
    findings.sort(key=Finding.sort_key)
    return findings
