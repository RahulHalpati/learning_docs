# 02-4 · Security gates (SAST + SCA)

> **Level:** Intermediate · **Prerequisites:** [02-3 Caching & speed](03_caching_and_speed.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (bandit, pip-audit)

Security belongs *in* the pipeline, not in a once-a-year audit. This stage runs the
exact tools from the [Secure Code Audit course](../../secure_code_audit/) — SAST on
your code, SCA on your dependencies — on every push.

---

## Two scans, two questions

| Scan | Question | Tool |
|---|---|---|
| **SAST** | Is *our code* dangerous? (eval, shell=True, hardcoded secrets) | bandit |
| **SCA** | Is a *dependency* known-vulnerable? (a CVE) | pip-audit |

(If you did the audit course, you also have your own `codeaudit` tool — drop it in
alongside bandit; it emits SARIF too.)

---

## Run locally

```bash
make security      # bandit -r app  +  pip-audit -r requirements.txt
```

Verified on the clean app:

```
$ bandit -q -r app
(no issues)
$ pip-audit -r requirements.txt
No known vulnerabilities found
```

---

## The CI job — and a key policy choice

From [`ci.yml`](../99_project_cicd_pipeline/.github/workflows/ci.yml):

```yaml
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: pip }
      - run: pip install -r requirements-dev.txt
      # SAST → SARIF, uploaded for review (informational)
      - run: bandit -r app -f sarif -o bandit.sarif || true
      - uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: bandit.sarif }
      # SCA → a known CVE FAILS the build (hard gate)
      - run: pip-audit -r requirements.txt
```

Notice the **two failure styles** — this is the important decision in every
security stage:

- **SAST is informational** (`|| true`, then upload SARIF). SAST is noisier
  (false positives), so blocking every merge on it frustrates developers. Upload
  results to the Security tab for review instead.
- **SCA is a hard gate** (no `|| true`). A known-CVE dependency is a clear,
  low-false-positive signal — block the merge until it's upgraded.

There's no universally right answer; the point is to **choose deliberately** which
findings block and which inform (the [triage](../../secure_code_audit/04_tools_and_dependencies/04_triage_and_false_positives.md)
lesson from the audit course applies directly).

---

## Why SARIF

`bandit -f sarif` + `upload-sarif` makes findings appear **inline on the PR** and
in the repo's **Security tab** — no custom dashboard. SARIF is the standard
interchange format; any scanner that emits it (bandit, semgrep, your `codeaudit`,
CodeQL) plugs into the same GitHub UI. Emit SARIF and the reporting is free.

> **GitHub CodeQL** is the heavier, deeper SAST option — enable it via the
> `github/codeql-action` for interprocedural analysis. bandit is the fast
> first line; CodeQL is the deep sweep. Run both if the project warrants it.

---

## Recap & next

- ✅ **SAST (bandit)** scans your code; **SCA (pip-audit)** scans dependencies —
  both on every push, reusing the audit course's tools.
- ✅ **Choose what blocks:** SCA a hard gate (low false positives), SAST
  informational via SARIF (noisier) — a deliberate policy call.
- ✅ **SARIF** surfaces findings in the PR and Security tab for free.

**Self-check:** Why gate the merge on `pip-audit` but not on `bandit` in this
pipeline?

<details>
<summary>Answer</summary>

`pip-audit` reports **known CVEs in dependencies** — a precise, low-false-positive
signal that clearly should block. `bandit` (SAST) is heuristic and noisier; hard-
gating on it would block merges on false positives and erode trust, so its results
are uploaded for review instead. It's a deliberate block-vs-inform policy choice,
not a claim that SAST matters less.

</details>

**→ Next: [03-1 · Artifacts & versioning](../03_build_and_artifacts/01_artifacts_and_versioning.md)**
