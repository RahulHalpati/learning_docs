# 02-2 · Testing & coverage (matrix)

> **Level:** Beginner · **Prerequisites:** [02-1 Lint & format](01_lint_and_format.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (pytest, coverage 98%)

Tests are the heart of CI — the evidence a change is safe. This stage runs them
across several Python versions and enforces a coverage floor.

---

## Run the tests locally

```bash
make test          # pytest
```

Verified:

```
$ pytest
........                                                    [100%]
8 passed in 0.16s
```

Eight tests: fast unit tests on `core.py` (URL validation, slug generation) and
integration tests on the HTTP layer via Flask's test client — no server needed:

```python
def test_shorten_and_follow(client):
    resp = client.post("/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 201
    slug = resp.get_json()["slug"]
    assert client.get(f"/{slug}").status_code == 302
```

---

## Coverage as a gate

Coverage measures which lines the tests exercise. Make it a **gate** so coverage
can't silently rot:

```bash
make cov       # coverage run -m pytest ; coverage report --fail-under=80
```

Verified:

```
Name              Stmts   Miss  Cover
-------------------------------------
app/__init__.py       1      0   100%
app/core.py          21      0   100%
app/main.py          29      1    97%
-------------------------------------
TOTAL                51      1    98%
```

`--fail-under=80` fails the job below 80%. A word of caution: **coverage is a
floor, not a goal.** 100% coverage of shallow tests proves little; treat the
number as "did we forget to test something large," not as a quality score.

---

## The matrix: test on many versions at once

A **matrix** runs the same job across a set of values — here, three Python
versions in parallel:

```yaml
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false                    # let all versions finish, don't cancel siblings
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pip install -r requirements-dev.txt && pip install -e .
      - run: coverage run -m pytest
      - run: coverage report --fail-under=80
```

One job definition → three parallel runs (3.10, 3.11, 3.12). `fail-fast: false`
means if 3.10 fails you still see whether 3.11/3.12 pass — useful for spotting
version-specific breakage. Matrices also cover OSes (`os: [ubuntu, macos, windows]`)
and dependency versions.

---

## Recap & next

- ✅ Split **fast unit tests** (pure logic) from **integration tests** (the app via
  a test client) — no running server needed.
- ✅ Make **coverage a gate** (`--fail-under`), but treat the % as a floor, not a
  quality score.
- ✅ A **matrix** runs the job across versions/OSes in parallel; `fail-fast: false`
  shows you every version's result.

**Self-check:** Your matrix has `fail-fast: true` (the default). 3.10 fails fast and
GitHub cancels the 3.11 and 3.12 jobs. Why might you set `fail-fast: false` instead?

<details>
<summary>Answer</summary>

To see **every** version's result in one run. With `fail-fast: false`, a failure on
3.10 doesn't cancel 3.11/3.12, so you can tell whether the bug is version-specific
(only 3.10) or universal — without pushing again to re-trigger the others.

</details>

**→ Next: [02-3 · Caching & speed](03_caching_and_speed.md)**
