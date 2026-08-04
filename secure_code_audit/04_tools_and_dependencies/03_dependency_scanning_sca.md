# 04-3 · Dependency scanning (SCA)

> **Level:** Beginner · **Prerequisites:** [04-1 bandit](01_bandit.md)
> **Time:** 25 min · **Verified:** 2026-07-15 (codeaudit offline check; pip-audit 2.10.1)

Most of your app's code isn't yours — it's your dependencies. **SCA** (Software
Composition Analysis) checks those dependencies against databases of known
vulnerabilities (CVEs). It's often the highest-value, lowest-effort security win:
no code review, just "are we running a version with a known hole?"

---

## Your tool's offline SCA

`codeaudit` ships a tiny **bundled** vulnerability dataset so the check runs with
no network — [`data/known_vulns.json`](../99_project_codeaudit/data/known_vulns.json):

```json
{
  "PyYAML": [
    {"id": "CVE-2020-14343", "fixed_in": "5.4", "severity": "high",
     "cwe": "CWE-502", "summary": "Arbitrary code execution via full/unsafe load ..."}
  ]
}
```

The logic ([`dependencies.py`](../99_project_codeaudit/codeaudit/dependencies.py)) is
just: parse `name==version`, compare the pinned version to `fixed_in`, flag if
lower.

```bash
python -m codeaudit.cli samples/vulnerable_app --deps samples/vulnerable_app/requirements.txt
```

Real output — 4 findings from the bundled dataset:

```
🟠 HIGH   CVE-2020-14343  PyYAML==5.3.1 is vulnerable (...). Upgrade to >= 5.4.
🟠 HIGH   CVE-2019-10906  Jinja2==2.10 is vulnerable (...). Upgrade to >= 2.10.1.
🟡 MEDIUM CVE-2018-1000656 Flask==0.12.2 is vulnerable (...). Upgrade to >= 0.12.3.
🟡 MEDIUM CVE-2018-18074  requests==2.19.0 is vulnerable (...). Upgrade to >= 2.20.0.
```

The version compare is deliberately simple (`_version_tuple` + `<`), so you can
read it. The *method* — pin vs. known-bad-range — is exactly what real tools do.

---

## The real thing: pip-audit against a live database

A bundled dataset goes stale instantly. Real SCA queries a maintained feed (the
**OSV** / PyPI advisory database). `pip-audit` does this:

```bash
pip install pip-audit
pip-audit -r samples/vulnerable_app/requirements.txt
```

Real output (excerpt) — and notice the scale difference:

```
Found 35 known vulnerabilities in 6 packages
Name     Version ID              Fix Versions
-------- ------- --------------- -------------
flask    0.12.2  PYSEC-2019-179  1.0
pyyaml   5.3.1   PYSEC-2021-142  5.4
requests 2.19.0  PYSEC-2018-28   2.20.0
jinja2   2.10    PYSEC-2019-217  2.10.1
idna     2.7     PYSEC-2024-60   3.7          ← transitive! not in our requirements
urllib3  1.23    PYSEC-2023-192  1.26.17,2.0.6 ← transitive!
...
```

**Your tool found 4; pip-audit found 35 across 6 packages.** Two reasons, both
important:

1. **Live, complete database.** OSV tracks every advisory; our four hand-picked
   entries are a teaching sample.
2. **Transitive dependencies.** `idna` and `urllib3` aren't in the requirements
   file — they're pulled in *by* `requests`. Real SCA resolves the full dependency
   tree; the vulnerability you inherit is just as real as the one you chose.

---

## Making SCA routine

- **Lock your dependencies** (`pip-compile`/`requirements.txt` with hashes, or a
  lockfile) so scans are reproducible and you know exactly what's installed.
- **Automate it** — `pip-audit` in CI (Section 05-2) and/or GitHub **Dependabot**
  to open upgrade PRs automatically.
- **Watch the supply chain** — beyond known CVEs, prefer maintained packages;
  typosquats and abandoned libraries are real risks a CVE feed won't flag.

---

## Recap & next

- ✅ **SCA** checks your dependencies against known-CVE databases — high value,
  low effort.
- ✅ Your offline check shows the *method*; **pip-audit** shows the reality: **35
  vs 4**, because of a **live DB** and **transitive dependencies**.
- ✅ **Lock** dependencies, **automate** scanning (pip-audit in CI + Dependabot),
  and mind the broader **supply chain**.

## Exercise

Your `known_vulns.json` misses the transitive `urllib3`/`idna` findings pip-audit
caught. Why can't a *requirements.txt*-only scan (yours or pip-audit's `-r` mode)
see the full picture, and what input would?

<details>
<summary>Solution</summary>

`requirements.txt` often lists only **direct** dependencies; transitive ones
(`urllib3` via `requests`) may not appear, so a file-only scan misses them. To see
the full tree you scan the **installed environment** (`pip-audit` with no `-r`,
against the active venv) or a **lockfile** that pins the entire resolved tree
(hashes included). That's why locking + environment scanning beats scanning the
hand-written requirements alone.

</details>

**→ Next: [04-4 · Triage & false positives](04_triage_and_false_positives.md)**
