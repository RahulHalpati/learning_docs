# 04-1 · bandit

> **Level:** Beginner · **Prerequisites:** [03-4 Simple taint tracking](../03_static_analysis_with_ast/04_simple_taint_tracking.md)
> **Time:** 20 min · **Verified:** 2026-07-15 (bandit 1.9.4)

**bandit** is the standard SAST tool for Python — the mature, community-maintained
version of the tool you just built. Because you built one, it holds no mystery:
it's rules over an AST, with a big rule library.

---

## Install and run

```bash
pip install bandit
bandit --version                       # bandit 1.9.4
bandit -r samples/vulnerable_app
```

Real output (excerpt) on the same sample app:

```
>> Issue: [B105:hardcoded_password_string] Possible hardcoded password: 'super-secret-key-12345'
   Severity: Low   Confidence: Medium
   CWE: CWE-259 (https://cwe.mitre.org/data/definitions/259.html)
   Location: samples/vulnerable_app/app.py:21:17
20	# VULN: hardcoded secret (CA106, CWE-798)
21	app.secret_key = "super-secret-key-12345"

>> Issue: [B403:blacklist] Consider possible security implications associated with pickle module.
   Severity: Low   Confidence: High
   CWE: CWE-502
   Location: samples/vulnerable_app/app.py:10:0
```

Totals in the verified run: **15 issues (4 High, 7 Medium, 4 Low)**.

---

## bandit vs. your `codeaudit` — a real comparison

Same target, two tools:

| | `codeaudit` (yours) | bandit 1.9.4 |
|---|---|---|
| Total findings | 14 | 15 |
| Rule library | 7 patterns + 3 taint | ~70 plugins (B1xx–B7xx) |
| Import-level flags (`import pickle`/`subprocess`) | no | **yes** (B403/B404) |
| Taint (user input → SQL/open/HTTP) | **yes** (CA201–203) | limited (mostly pattern/heuristic) |
| Severity **and** confidence | severity only | severity **+ confidence** |
| Output formats | text/json/sarif | text/json/csv/html/**sarif**/xml |

Two takeaways:

1. **bandit casts a wider net** — it flags even *importing* `pickle`/`subprocess`
   (B403/B404) as a prompt to review. More coverage, but more noise.
2. **Your taint rules add something bandit's defaults are weak at** — following
   `request.args` into `open()`/`requests.get()`. No single tool is a superset;
   this is why teams run several.

---

## Reading a bandit finding

Each issue has three things worth internalising:

- **Test id** (`B105`, `B403`) — the rule; look it up to understand/tune it.
- **Severity** — how bad if real.
- **Confidence** — how sure bandit is it's real. **Low confidence = likely false
  positive**; this second axis (which your tool lacks) is how you triage volume.

Filter to what matters:

```bash
bandit -r samples/vulnerable_app -ll        # only Medium+ severity
bandit -r samples/vulnerable_app -iii       # only High confidence
bandit -r samples/vulnerable_app -f sarif -o bandit.sarif   # SARIF for CI
```

---

## Tuning: baselines and suppressions

Real projects start with existing findings. Two standard moves:

- **Baseline** — record current findings and only fail on *new* ones:
  `bandit -r . -b baseline.json`.
- **Inline suppress** a reviewed false positive: `# nosec B608` on the line (always
  with the specific test id and a reason — never a bare `# nosec`).

---

## Recap & next

- ✅ **bandit** is production Python SAST — the same architecture you built, with
  ~70 rules.
- ✅ On the sample app: **bandit 15, codeaudit 14** — overlapping but not identical;
  bandit is broader, your taint rules catch flows bandit's defaults miss.
- ✅ **Confidence** (not just severity) drives triage; tune with `-ll`/`-iii`,
  **baselines**, and specific `# nosec` suppressions.

## Exercise

Run `bandit -r samples/vulnerable_app -f json` and count issues by `issue_severity`.
Which finding does bandit report that `codeaudit` doesn't, and why?

<details>
<summary>Solution</summary>

```bash
bandit -r samples/vulnerable_app -f json | \
  python -c "import sys,json,collections;d=json.load(sys.stdin);print(collections.Counter(r['issue_severity'] for r in d['results']))"
# Counter({'MEDIUM': 7, 'LOW': 4, 'HIGH': 4})
```

bandit flags the **imports** of `pickle` (B403) and `subprocess` (B404), which
`codeaudit` ignores — our tool only flags the dangerous *calls*, not the imports.
bandit treats a risky import as a prompt to review; it's broader but noisier.

</details>

**→ Next: [04-2 · semgrep & custom rules](02_semgrep.md)**
