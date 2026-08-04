# 99 · Capstone — the `codeaudit` tool

A complete, readable static analysis tool in pure-stdlib Python. It reads Python
source with `ast`, flags vulnerability patterns, tracks taint from source to sink,
scans dependencies, emits SARIF for CI, and can add optional LLM triage.

```
scan_path → [ pattern rules ] + [ taint ] → Findings → text / json / sarif
                                                    └── optional --explain (LLM)
```

---

## Layout

```
99_project_codeaudit/
├── codeaudit/
│   ├── finding.py        # the Finding dataclass + severity ordering
│   ├── rules.py          # 7 AST pattern rules (CA101–CA107) + ALL_RULES
│   ├── taint.py          # intraprocedural source→sink taint (CA201–CA203)
│   ├── scanner.py        # walk a path, parse, run rules + taint
│   ├── dependencies.py   # SCA: requirements.txt vs bundled known_vulns.json
│   ├── report.py         # text / json / sarif formatters
│   ├── providers.py      # LLM backend for --explain (fake | ollama | anthropic | openai)
│   └── cli.py            # python -m codeaudit.cli <path> [--format …] [--deps …] [--explain]
├── data/known_vulns.json # tiny offline CVE-by-version dataset (SCA demo)
├── samples/vulnerable_app/  # intentionally-vulnerable Flask app (annotated # VULN)
├── tests/                # 16 offline tests (rules, taint, end-to-end)
└── requirements.txt      # only pytest; scanners/LLM are optional & commented
```

---

## Quick start (offline, zero dependencies)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # just pytest — the auditor needs nothing

python -m codeaudit.cli samples/vulnerable_app
python -m codeaudit.cli samples/vulnerable_app --format sarif
python -m codeaudit.cli samples/vulnerable_app --deps samples/vulnerable_app/requirements.txt
python -m codeaudit.cli samples/vulnerable_app --explain          # offline fake triage
python -m pytest -q
```

### Verified output (2026-07-15, Python 3.10.12)

```
$ python -m codeaudit.cli samples/vulnerable_app
── 14 findings (2 critical, 7 high, 5 medium) ──

$ python -m codeaudit.cli samples/vulnerable_app --deps samples/vulnerable_app/requirements.txt
   ... + 4 dependency findings (CVE-2020-14343, CVE-2019-10906, CVE-2018-1000656, CVE-2018-18074)

$ python -m pytest -q
16 passed
```

---

## What it detects

| Rule | CWE | Detects |
|---|---|---|
| CA101 | CWE-95 | `eval` / `exec` / `os.system` |
| CA102 | CWE-78 | `subprocess(..., shell=True)` |
| CA103 | CWE-327 | weak hash (`md5`/`sha1`) |
| CA104 | CWE-502 | `pickle.loads`, `yaml.load` without SafeLoader |
| CA105 | CWE-489 | Flask `debug=True` |
| CA106 | CWE-798 | hardcoded secret (literal → secret-y name) |
| CA107 | CWE-89 | SQL built by f-string/concat/`.format` |
| CA201 | CWE-89 | **taint:** user input → SQL `execute()` |
| CA202 | CWE-22 | **taint:** user input → `open()` (path traversal) |
| CA203 | CWE-918 | **taint:** user input → outbound HTTP (SSRF) |

Plus a **dependency (SCA)** check against `data/known_vulns.json`.

---

## Configuration

| Env var | Default | Options |
|---|---|---|
| `CODEAUDIT_LLM` | `fake` | `fake`, `ollama`, `anthropic`, `openai` |
| `OLLAMA_MODEL` | `qwen2:7b` | any local Ollama model |

CLI flags: `--format {text,json,sarif}`, `--min-severity`, `--deps <req.txt>`,
`--explain`, `--exit-zero`.

---

## Extending it (course exercises)

1. **New pattern rule** — subclass `Rule`, append to `ALL_RULES` ([03-3](../03_static_analysis_with_ast/03_writing_detection_rules.md)); e.g. `CA108` for `verify=False`.
2. **New taint sink** — add to the sink maps in `taint.py` ([03-4](../03_static_analysis_with_ast/04_simple_taint_tracking.md)); e.g. `subprocess` command injection.
3. **IDOR reminder** — flag routes with `<id>` params that hit the DB ([02-6](../02_reading_code_for_vulns/06_access_control_idor.md)).
4. **CI gate** — the GitHub Actions workflow in [05-2](../05_llm_assisted_and_shipping/02_ci_integration_and_reporting.md).

---

> ⚠️ `samples/vulnerable_app/` is intentionally vulnerable — a practice target only.
> Never deploy it or reuse its patterns. Audit only code you're authorised to review.

→ Course starts at the **[README](../README.md)** → **[00 · Introduction](../00_introduction.md)**.
