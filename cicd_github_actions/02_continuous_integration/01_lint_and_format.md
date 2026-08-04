# 02-1 · Lint & format

> **Level:** Beginner · **Prerequisites:** [01-4 Sample app & Makefile](../01_foundations/04_sample_app_and_makefile.md)
> **Time:** 20 min · **Verified:** 2026-07-16 (ruff)

The cheapest, fastest stage goes first: static style and lint checks. They catch
whole classes of mistakes in seconds and end all formatting debates.

---

## Lint vs. format

- **Linting** finds *likely bugs and bad patterns* — an unused import, a bare
  `except`, a mutable default argument.
- **Formatting** enforces *consistent style* — quotes, spacing, line length — so
  diffs stay small and nobody argues about it in review.

We use **ruff** for both: it's extremely fast and replaces flake8 + isort + black
in one tool. Config lives in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP"]   # pycodestyle, pyflakes, isort, bugbear, pyupgrade
```

---

## Run it locally

```bash
make lint      # ruff check app tests  +  ruff format --check
```

Verified:

```
$ ruff check app tests
All checks passed!
```

`ruff check` lints; `ruff format --check` verifies formatting **without changing
files** (it fails if anything is mis-formatted). To actually fix formatting:
`make format`.

---

## The CI job

Straight from [`ci.yml`](../99_project_cicd_pipeline/.github/workflows/ci.yml) —
note it just runs the same tools:

```yaml
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip                       # cache deps (02-3)
      - run: pip install -r requirements-dev.txt
      - run: ruff check app tests
      - run: ruff format --check app tests   # --check = fail, don't rewrite
```

`--check` is the CI-correct flavour: in CI you want it to **fail** on bad
formatting, not silently reformat and hide the problem.

---

## Why lint first?

It's the fastest possible feedback, and it's a hard gate: a lint failure stops the
pipeline before the (slower) test and build stages waste runner minutes. Ordering
by cost — lint → test → build — means the common, cheap mistakes fail first.

> Going further: a **pre-commit hook** runs ruff on `git commit` so issues never
> even reach CI. Same tool, one step earlier. (See [05-2](../05_advanced_and_shipping/02_hardening_gates_and_dora.md).)

---

## Recap & next

- ✅ **Lint** finds likely bugs; **format** enforces style — **ruff** does both,
  fast.
- ✅ Use `ruff format --check` in CI so bad formatting **fails** rather than being
  silently rewritten.
- ✅ Lint runs **first** — cheapest feedback, gates the expensive stages.

**Self-check:** Why `ruff format --check` in CI instead of plain `ruff format`?

<details>
<summary>Answer</summary>

`ruff format` **rewrites** files to fix formatting; in CI there's no one to commit
those changes, so it would "pass" while leaving the repo unformatted. `--check`
makes the job **fail** on mis-formatted code, which is the signal you want — fix it
locally and push.

</details>

**→ Next: [02-2 · Testing & coverage](02_testing_and_coverage.md)**
