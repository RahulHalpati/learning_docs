"""Software Composition Analysis (SCA): flag dependencies pinned to versions
with known vulnerabilities.

Offline by default: it compares each pinned package against a small **bundled**
dataset (`data/known_vulns.json`) so the demo runs with no network. The real
world uses a live feed — `pip-audit` / the OSV database — which module 04-3
shows as the drop-in upgrade. The comparison logic is the same either way.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .finding import Finding

_DATA = Path(__file__).resolve().parent.parent / "data" / "known_vulns.json"
_REQ_LINE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([0-9][0-9A-Za-z.\-]*)")


def _version_tuple(v: str) -> tuple[int, ...]:
    parts = re.split(r"[.\-]", v)
    nums = []
    for p in parts:
        m = re.match(r"\d+", p)
        nums.append(int(m.group()) if m else 0)
    return tuple(nums)


def _lt(a: str, b: str) -> bool:
    """a < b by version ordering, zero-padded to equal length."""
    ta, tb = _version_tuple(a), _version_tuple(b)
    length = max(len(ta), len(tb))
    ta += (0,) * (length - len(ta))
    tb += (0,) * (length - len(tb))
    return ta < tb


def load_dataset(path: str | Path | None = None) -> dict:
    with open(path or _DATA, encoding="utf-8") as fh:
        return json.load(fh)


def parse_requirements(text: str) -> list[tuple[str, str]]:
    """Return [(name, pinned_version)] for lines like `Flask==0.12.2`."""
    pins = []
    for line in text.splitlines():
        line = line.split("#", 1)[0]
        m = _REQ_LINE.match(line)
        if m:
            pins.append((m.group(1), m.group(2)))
    return pins


def check_requirements(path: str | Path, dataset: dict | None = None) -> list[Finding]:
    dataset = dataset or load_dataset()
    # normalise dataset keys to lowercase for case-insensitive matching
    db = {k.lower(): v for k, v in dataset.items()}
    text = Path(path).read_text(encoding="utf-8")
    findings: list[Finding] = []
    for name, version in parse_requirements(text):
        for vuln in db.get(name.lower(), []):
            if _lt(version, vuln["fixed_in"]):
                findings.append(Finding(
                    rule_id=vuln.get("id", "CVE-UNKNOWN"),
                    severity=vuln.get("severity", "medium"),
                    message=f"{name}=={version} is vulnerable ({vuln['summary']}). "
                            f"Upgrade to >= {vuln['fixed_in']}.",
                    file=str(path),
                    line=0,
                    snippet=f"{name}=={version}",
                    cwe=vuln.get("cwe", ""),
                ))
    findings.sort(key=Finding.sort_key)
    return findings


def main(argv: list[str] | None = None) -> int:
    import sys
    from .report import format_text
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m codeaudit.dependencies <requirements.txt>")
        return 2
    findings = check_requirements(args[0])
    print(format_text(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
