# 05-2 · CI integration & reporting

> **Level:** Intermediate · **Prerequisites:** [05-1 LLM-assisted code review](01_llm_assisted_review.md)
> **Time:** 20 min · **Verified:** 2026-07-15 (SARIF output verified; workflow is standard GitHub Actions)

An audit you run by hand once is a snapshot; an audit that runs on **every push**
is a safety net. This is "shift left" made real — and the bridge to the
[CI/CD course](../../). By the end, a risky commit fails the build before it merges.

---

## Why SARIF

Your tool already emits **SARIF** (Static Analysis Results Interchange Format) — the
standard JSON that GitHub, GitLab, and IDEs ingest. Verified output:

```bash
python -m codeaudit.cli samples/vulnerable_app --format sarif | head
```

```json
{
  "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
  "version": "2.1.0",
  "runs": [{ "tool": { "driver": { "name": "codeaudit", "rules": [{"id": "CA101"}, ...] } },
             "results": [ ... ] }]
}
```

Emit SARIF and GitHub renders your findings inline on the PR and in the Security
tab — no custom UI needed. It's why "support SARIF" is the single most useful thing
a scanner can do for CI.

---

## A GitHub Actions security workflow

`.github/workflows/security.yml` — runs your auditor and SCA on every push/PR:

```yaml
name: security
on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }

      # 1. your SAST tool → SARIF → GitHub Security tab
      - name: Static audit (codeaudit)
        run: |
          cd 99_project_codeaudit
          python -m codeaudit.cli . --format sarif > codeaudit.sarif || true
      - uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: 99_project_codeaudit/codeaudit.sarif }

      # 2. dependency scan — fail the build on a known CVE
      - name: Dependency audit (pip-audit)
        run: |
          pip install pip-audit
          pip-audit -r 99_project_codeaudit/samples/vulnerable_app/requirements.txt

      # 3. run the tests
      - name: Tests
        run: |
          cd 99_project_codeaudit && pip install -r requirements.txt && python -m pytest -q
```

Note the two failure styles: SAST uploads results for review (`|| true`, informational),
while `pip-audit` **fails the job** on a known-vulnerable dependency — a hard gate.
Choosing which findings *block* a merge vs. which *inform* is the key policy
decision, and it's exactly what the [CI/CD course](../../) goes deep on.

---

## Run the same checks locally (pre-commit)

Catch it before it's even pushed. A `.pre-commit-config.yaml` hook, or a Makefile:

```makefile
audit:
	python -m codeaudit.cli . --min-severity high
	pip-audit -r requirements.txt

test:
	python -m pytest -q

check: audit test      # run before every push
```

Local `make check` = the same gates as CI, seconds after you type the code. Same
commands in both places means "works in CI" and "works on my machine" stop
diverging.

---

## Responsible disclosure (when you find a *real* one)

If your auditing finds a genuine vulnerability in **someone else's** software:

1. **Don't exploit it** beyond confirming it exists.
2. **Report privately** to the maintainer (a `SECURITY.md`, security@ address, or a
   coordinated-disclosure platform) — not a public issue.
3. **Give reasonable time** to fix before any public write-up.
4. Follow any **bug-bounty / disclosure policy** the project publishes.

Finding a bug is skill; disclosing it responsibly is professionalism.

---

## Recap & next

- ✅ **SARIF** makes your tool a first-class CI citizen — GitHub renders findings on
  the PR and Security tab.
- ✅ A CI workflow runs **SAST (inform) + SCA (gate) + tests**; deciding what
  *blocks* a merge is the core policy choice.
- ✅ Mirror the gates **locally** (`make check` / pre-commit); disclose real
  third-party findings **responsibly**.

## Exercise

Make the SAST step a hard gate for high-severity findings only (medium/low stay
informational). Which `codeaudit` flags achieve this?

<details>
<summary>Solution</summary>

Run a second, gating invocation using `--min-severity high` and drop the `|| true`
so a non-zero exit fails the job:

```yaml
- name: Fail on high-severity findings
  run: cd 99_project_codeaudit && python -m codeaudit.cli . --min-severity high
```

`--min-severity high` keeps only critical/high findings, and the CLI already exits
non-zero when any remain (unless `--exit-zero`), which fails the step. The earlier
SARIF upload still records everything for review.

</details>

**→ Next: [05-3 · AI pentesting in CI with Strix](03_ai_pentest_in_ci_strix.md)** — add a
*dynamic* AI pentester alongside these static gates.
