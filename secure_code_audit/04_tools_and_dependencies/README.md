# 04 · Industry tools & dependencies

You built a scanner; now meet the ones the industry uses. You'll run bandit and
semgrep on the same sample app, compare them to your tool, scan dependencies for
CVEs, and learn to triage the flood of findings any scanner produces.

| # | Module | You'll be able to… |
|---|---|---|
| 04-1 | [bandit](01_bandit.md) | Run/read/tune bandit; compare it to `codeaudit` |
| 04-2 | [semgrep & custom rules](02_semgrep.md) | Run semgrep and write a custom rule |
| 04-3 | [Dependency scanning (SCA)](03_dependency_scanning_sca.md) | Find known-vulnerable dependencies with pip-audit |
| 04-4 | [Triage & false positives](04_triage_and_false_positives.md) | Prioritise, suppress, and report findings |

> These modules install optional tools (`pip install bandit pip-audit`, and
> `semgrep`). Everything from Sections 01–03 still runs without them.

**Next → [04-1 · bandit](01_bandit.md)**
