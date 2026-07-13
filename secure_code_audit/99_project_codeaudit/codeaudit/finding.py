"""The one data structure the whole tool passes around: a Finding.

Every rule, the taint tracker, and the dependency checker all produce Findings;
the reporter consumes them. Keeping this in its own tiny module avoids import
cycles (rules → finding ← report).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

# lower number = more urgent; used to sort and to filter with --severity
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


@dataclass
class Finding:
    rule_id: str          # stable id, e.g. "CA101" (also used as the SARIF ruleId)
    severity: str         # critical | high | medium | low | info
    message: str          # human-readable, says what and why
    file: str             # path to the file
    line: int             # 1-based line number
    snippet: str = ""     # the offending source line, stripped
    cwe: str = ""         # e.g. "CWE-89" — ties the finding to a known weakness class

    def sort_key(self) -> tuple:
        return (SEVERITY_ORDER.get(self.severity, 9), self.file, self.line)

    def to_dict(self) -> dict:
        return asdict(self)
