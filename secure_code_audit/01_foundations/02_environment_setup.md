# 01-2 · Environment setup

> **Level:** Beginner · **Prerequisites:** [01-1 What is code audit?](01_what_is_code_audit.md)
> **Time:** 20 min · **Verified:** 2026-07-15 (Python 3.10.12)

Let's get the project running and see a real scan before learning how it works.

---

## 1. Python only

The auditor core uses **only the standard library** (`ast`, `tokenize`, `re`,
`json`). You need Python 3.10+:

```bash
python3 --version
# Python 3.10.12
```

```bash
cd 99_project_codeaudit
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt                       # just pytest (+ optional extras, commented out)
```

That's it — no scanners, no API keys. The optional tools (bandit, semgrep,
pip-audit, a local LLM) are commented out in `requirements.txt`; you install them
only when Sections 04–05 ask.

---

## 2. Meet the target

You audit a bundled, **intentionally vulnerable** Flask app at
`samples/vulnerable_app/app.py`. Every flaw is annotated:

```python
# VULN: SQL injection — f-string into execute (CA107 + taint CA201, CWE-89)
cur.execute(f"SELECT * FROM users WHERE name = '{username}'")
```

Those `# VULN:` comments are your answer key — but the goal is to spot such lines
*without* the comment. (In Section 04 we'll strip the comments in an exercise.)

> ⚠️ This app is a practice target only. Never deploy it or reuse its code.

---

## 3. Run a scan

```bash
python -m codeaudit.cli samples/vulnerable_app
```

Real output (abridged):

```
🔴 CRITICAL CA101  samples/vulnerable_app/app.py:76
    Dangerous call to `eval()` — arbitrary code/command execution risk.
    | return str(eval(tmpl))
    (CWE-95)
...
── 14 findings (2 critical, 7 high, 5 medium) ──
```

The process exits **non-zero when findings exist** (like a linter) so it can fail
a CI job. Add `--exit-zero` to override.

Other formats:

```bash
python -m codeaudit.cli samples/vulnerable_app --format json     # for scripts
python -m codeaudit.cli samples/vulnerable_app --format sarif    # for CI / GitHub code scanning
python -m codeaudit.cli samples/vulnerable_app --min-severity high   # filter noise
```

---

## 4. Run the tests

```bash
python -m pytest -q
```

```
16 passed in 0.08s
```

If that passes, your environment is correct and you can focus on *learning*.

---

## Recap & next

- ✅ The auditor core is **stdlib-only**; the optional scanners install later.
- ✅ You scanned the bundled vulnerable app (**14 findings**) and ran the tests
  (**16 passed**), all offline.
- ✅ Output comes as **text / json / sarif**, with a **non-zero exit** for CI.

**Self-check:** Why does the CLI exit with a non-zero status when it finds
something?

<details>
<summary>Answer</summary>

So it can act as a **CI gate** — a non-zero exit fails the pipeline step, blocking
a merge until the findings are addressed (or explicitly suppressed). `--exit-zero`
turns this off for report-only runs.

</details>

**→ Next: [01-3 · Vulnerability classes](03_vulnerability_classes.md)**
