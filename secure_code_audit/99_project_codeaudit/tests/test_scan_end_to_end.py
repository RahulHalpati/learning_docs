"""End-to-end: scan the bundled vulnerable app, check outputs and the SCA check."""

import json
from pathlib import Path

from codeaudit.dependencies import check_requirements
from codeaudit.report import format_sarif
from codeaudit.scanner import scan_path

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "vulnerable_app"


def test_scan_finds_the_expected_rule_classes():
    findings = scan_path(SAMPLE)
    found = {f.rule_id for f in findings}
    # every rule family should be represented by the sample app
    for rid in ["CA101", "CA102", "CA103", "CA104", "CA105", "CA106", "CA107",
                "CA201", "CA202", "CA203"]:
        assert rid in found, f"expected {rid} in {sorted(found)}"
    assert len(findings) >= 12


def test_sarif_output_is_valid_json_with_results():
    findings = scan_path(SAMPLE)
    doc = json.loads(format_sarif(findings))
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["name"] == "codeaudit"
    assert len(doc["runs"][0]["results"]) == len(findings)


def test_dependency_check_flags_old_pins():
    findings = check_requirements(SAMPLE / "requirements.txt")
    ids = {f.rule_id for f in findings}
    assert "CVE-2020-14343" in ids   # PyYAML 5.3.1
    assert len(findings) >= 3
