"""Turn a list of Findings into a human table, JSON, or SARIF (for CI)."""

from __future__ import annotations

import json

from .finding import Finding

_ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}


def format_text(findings: list[Finding]) -> str:
    if not findings:
        return "✅ No findings."
    out = []
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
        icon = _ICON.get(f.severity, "•")
        out.append(f"{icon} {f.severity.upper():8} {f.rule_id}  {f.file}:{f.line}")
        out.append(f"    {f.message}")
        if f.snippet:
            out.append(f"    | {f.snippet}")
        if f.cwe:
            out.append(f"    ({f.cwe})")
        out.append("")
    summary = ", ".join(f"{n} {sev}" for sev, n in
                        sorted(counts.items(), key=lambda kv: kv[0]))
    out.append(f"── {len(findings)} findings ({summary}) ──")
    return "\n".join(out)


def format_json(findings: list[Finding]) -> str:
    return json.dumps([f.to_dict() for f in findings], indent=2)


def format_sarif(findings: list[Finding]) -> str:
    """Minimal SARIF 2.1.0 — the format GitHub code scanning and many CIs ingest."""
    rule_ids = sorted({f.rule_id for f in findings})
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "codeaudit",
                "informationUri": "https://example.com/codeaudit",
                "rules": [{"id": rid} for rid in rule_ids],
            }},
            "results": [{
                "ruleId": f.rule_id,
                "level": _sarif_level(f.severity),
                "message": {"text": f.message},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": f.file},
                    "region": {"startLine": max(1, f.line)},
                }}],
            } for f in findings],
        }],
    }
    return json.dumps(sarif, indent=2)


def _sarif_level(severity: str) -> str:
    return {"critical": "error", "high": "error",
            "medium": "warning", "low": "note", "info": "note"}.get(severity, "warning")


def render(findings: list[Finding], fmt: str = "text") -> str:
    return {"text": format_text, "json": format_json, "sarif": format_sarif}[fmt](findings)
