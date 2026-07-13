"""codeaudit — a tiny, readable Python source auditor built on the stdlib `ast`.

    from codeaudit import scan_path
    for f in scan_path("myapp/"):
        print(f.file, f.line, f.rule_id, f.message)

The whole tool runs with **no third-party dependencies**. Optional extras
(bandit/semgrep/pip-audit for comparison, a local LLM for `--explain`) are just
that — optional. See the course for how each piece works and where it stops.
"""

from .finding import Finding
from .scanner import scan_path, scan_source
from .dependencies import check_requirements

__all__ = ["Finding", "scan_path", "scan_source", "check_requirements"]
