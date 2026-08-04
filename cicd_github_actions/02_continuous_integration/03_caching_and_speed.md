# 02-3 · Caching & speed

> **Level:** Intermediate · **Prerequisites:** [02-2 Testing & coverage](02_testing_and_coverage.md)
> **Time:** 20 min · **Verified:** 2026-07-16

A slow pipeline is a pipeline people route around. Fast feedback keeps CI trusted
and used. Here are the levers that matter, in order of impact.

---

## 1. Cache dependencies

Re-downloading and re-installing packages on every run is the most common waste.
`setup-python`'s built-in cache keys on your requirements files:

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip                      # caches the pip download cache
```

For finer control (or other package managers) use `actions/cache` directly:

```yaml
      - uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: pip-${{ hashFiles('requirements-dev.txt') }}
          restore-keys: pip-
```

The cache **key** includes a hash of the deps file, so the cache busts exactly when
dependencies change — and is reused otherwise.

---

## 2. Cancel superseded runs

If you push three times to a PR, you don't need three full runs — only the latest
commit matters. `concurrency` cancels the in-flight ones:

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

One caveat you'll see again in CD: for **production deploys** you set
`cancel-in-progress: false` — you never want to cancel a half-finished deploy.
Cancel CI freely; never cancel a prod deploy.

---

## 3. Parallelise and skip

- **Parallel jobs** — lint, test, and security are independent, so they run at once
  (no `needs:` between them). Wall-clock ≈ the slowest, not the sum.
- **`paths-ignore`** — skip CI when only docs changed:
  ```yaml
  on:
    pull_request:
      paths-ignore: ["**.md", "docs/**"]
  ```
- **`fail-fast`** — for a matrix, `true` (default) stops the rest on first failure
  to save minutes; `false` when you want full visibility ([02-2](02_testing_and_coverage.md)).

---

## 4. Don't over-engineer speed

Order-of-magnitude wins (caching deps, parallel jobs) are worth it. Shaving 5
seconds with elaborate cache layering usually isn't — the complexity costs more
than the time saved. Reach for:

1. Dependency caching ✅ (almost always)
2. Parallel jobs ✅ (free — just don't add needless `needs:`)
3. `concurrency` cancel ✅ (free)
4. Docker layer caching (build stage — [03-2](../03_build_and_artifacts/02_docker_build_and_registry.md))

…then stop and measure before doing more.

---

## Recap & next

- ✅ **Cache dependencies** (keyed on the deps file hash) — the biggest, easiest
  win.
- ✅ **`concurrency: cancel-in-progress`** for CI (but **not** for prod deploys);
  keep independent jobs **parallel**.
- ✅ Skip with **`paths-ignore`**; chase order-of-magnitude wins, then stop.

**Self-check:** Why is `cancel-in-progress: true` right for CI on a PR but dangerous
for a production deploy job?

<details>
<summary>Answer</summary>

On a PR, a newer push makes the older run irrelevant, so cancelling it saves
minutes. Cancelling a **production deploy** mid-run can leave prod in a half-updated,
inconsistent state — so there you use `cancel-in-progress: false` and let it finish.

</details>

**→ Next: [02-4 · Security gates](04_security_gates.md)**
