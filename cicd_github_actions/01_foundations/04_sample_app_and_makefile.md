# 01-4 · The sample app & local Makefile

> **Level:** Beginner · **Prerequisites:** [01-3 GitHub Actions anatomy](03_github_actions_anatomy.md)
> **Time:** 20 min · **Verified:** 2026-07-16 (ruff, pytest, coverage 98%)

Meet the app you'll build a pipeline for, and the idea that makes this course
click: **the CI runs the same commands you run locally.**

---

## `linkstash` — small on purpose

A tiny Flask link-shortener ([`99_project_cicd_pipeline/`](../99_project_cicd_pipeline/README.md)).
The app is trivial so the *pipeline* is the focus:

```
99_project_cicd_pipeline/
├── app/
│   ├── core.py      # pure logic: URL validation, slug generation (easy to test/lint)
│   └── main.py      # Flask HTTP layer: /health, /shorten, /<slug>
├── tests/           # test_core.py (unit) + test_api.py (integration)
├── Makefile         # local mirror of every CI stage
├── Dockerfile       # multi-stage build → the image CI publishes
├── pyproject.toml   # ruff, pytest, coverage config
└── .github/workflows/  # ci.yml, cd.yml, release.yml
```

Splitting **pure logic** (`core.py`) from the **HTTP layer** (`main.py`) is a
testing habit worth stealing: pure functions need no server, so most tests are
fast unit tests with a few integration tests on top.

> The framework is Flask, but nothing in the pipeline depends on that — swap in
> FastAPI/Django and `ci.yml` is unchanged.

---

## The Makefile is the contract

The key design idea: **CI should not run secret commands.** Every stage is a
`make` target, so the pipeline just calls `make lint`, `make test`, etc. — the
exact things you run locally.

```make
ci: lint cov security          # what the CI job runs
	@echo "✅ CI passed locally"

lint:
	$(VENV)/bin/ruff check app tests
cov:
	$(PY) -m coverage run -m pytest
	$(PY) -m coverage report --fail-under=80
security:
	$(VENV)/bin/bandit -q -r app
	$(VENV)/bin/pip-audit -r requirements.txt
```

Run the whole CI stage on your laptop:

```bash
make install     # venv + dev tooling, once
make ci
```

Verified output:

```
All checks passed!                     # ruff — lint
8 passed in 0.16s                       # pytest
Name              Stmts   Miss  Cover
app/core.py          21      0   100%
app/main.py          29      1    97%
TOTAL                51      1    98%   # coverage gate ≥80%
No known vulnerabilities found          # pip-audit
✅ CI passed locally
```

---

## Why mirror CI locally?

- **No push-and-pray.** You see red in 10 seconds locally instead of 3 minutes
  after a push.
- **One source of truth.** When a check changes, it changes in the Makefile —
  local and CI stay in lockstep, so "passes on my machine" and "passes in CI"
  can't diverge.
- **Onboarding.** A new contributor runs `make ci`; no need to reverse-engineer the
  YAML.

The CI workflow then becomes a thin wrapper — you'll see in [02-1](../02_continuous_integration/01_lint_and_format.md)
it literally installs deps and runs the same tools.

---

## Recap & next

- ✅ `linkstash` splits **pure logic** (fast unit tests) from the **HTTP layer**
  (a few integration tests).
- ✅ The **Makefile is the contract**: every CI stage is a `make` target you can run
  locally — verified `make ci` is green (98% coverage).
- ✅ Mirroring CI locally kills "works on my machine" and speeds feedback.

**Self-check:** Why put every CI step behind a `make` target instead of writing the
commands directly in the workflow YAML?

<details>
<summary>Answer</summary>

So local and CI run the **identical** commands from a single source of truth. If
the workflow embedded its own commands, they'd drift from what developers run
locally, reintroducing "works on my machine." The Makefile also makes the pipeline
runnable/debuggable without pushing.

</details>

**→ Next: [02-1 · Lint & format](../02_continuous_integration/01_lint_and_format.md)**
