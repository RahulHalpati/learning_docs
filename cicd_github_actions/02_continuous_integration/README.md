# 02 · Continuous Integration

The CI half: the checks that run on every PR. You'll build each stage of
[`ci.yml`](../99_project_cicd_pipeline/.github/workflows/ci.yml) and understand why
it's there.

| # | Module | Stage |
|---|---|---|
| 02-1 | [Lint & format](01_lint_and_format.md) | ruff — style + common bugs |
| 02-2 | [Testing & coverage](02_testing_and_coverage.md) | pytest across a Python matrix + a coverage gate |
| 02-3 | [Caching & speed](03_caching_and_speed.md) | dependency cache, concurrency, fail-fast |
| 02-4 | [Security gates](04_security_gates.md) | bandit (SAST) + pip-audit (SCA) + SARIF |

**Next → [02-1 · Lint & format](01_lint_and_format.md)**
