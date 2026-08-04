# 03-1 · Artifacts & versioning

> **Level:** Intermediate · **Prerequisites:** [02-4 Security gates](../02_continuous_integration/04_security_gates.md)
> **Time:** 20 min · **Verified:** 2026-07-16

Each job runs on a fresh runner, so anything one job produces and another needs
must be passed explicitly. That's what **artifacts** are for. And whatever you
build needs a **version** you can trace back to a commit.

---

## Artifacts: passing files between jobs

Jobs don't share a filesystem. To hand a build output (a wheel, a coverage report,
a SARIF file) from one job to another — or to keep it for download — use
`upload-artifact` / `download-artifact`:

```yaml
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install build && python -m build      # produces dist/*.whl
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist }
      - run: ls dist/                                    # the wheel from the build job
```

Artifacts also power **build-once, deploy-many**: build the thing a single time,
then the staging and production jobs deploy that *same* artifact — never rebuild
per environment, or you risk shipping something you didn't test.

> Artifacts vs cache: **cache** speeds up re-runs (dependencies); **artifacts**
> are outputs you want to keep or pass on. Don't use one for the other.

---

## Versioning: make every build traceable

A build you can't trace to a commit is a debugging nightmare. Two common schemes,
often combined:

| Scheme | Example | Good for |
|---|---|---|
| **Commit SHA** | `linkstash:9f3a1c2` | every build — unambiguous, automatic |
| **Semantic version** | `linkstash:1.2.0` | releases humans reason about |

`linkstash` carries a semver in `app/__init__.py` and `pyproject.toml`
(`__version__ = "1.2.0"`), surfaced at runtime via `/health`:

```json
{"status": "ok", "version": "1.2.0"}
```

The capstone tags images **both** ways — `:latest` and `:${GITHUB_SHA::7}` (the
short commit SHA) — so "what's running in prod?" is answerable from the tag, and
you can redeploy an exact past build. Releases add the semver tag ([04-3](../04_delivery_and_deployment/03_release_and_versioning.md)).

---

## Semantic versioning in one line

`MAJOR.MINOR.PATCH`: **MAJOR** = breaking change, **MINOR** = new feature
(backward-compatible), **PATCH** = bug fix. Bumping the right number tells
consumers what to expect from an upgrade — the contract behind `>=1.0,<2.0`.

---

## Recap & next

- ✅ Jobs don't share disk — use **artifacts** (`upload`/`download`) to pass outputs
  and to **build once, deploy many**.
- ✅ Artifacts (outputs to keep) ≠ cache (speed up re-runs).
- ✅ Version every build by **commit SHA** (traceable, automatic) and **semver**
  (human releases); `linkstash` exposes its version at `/health`.

**Self-check:** Why tag the image with the commit SHA, not just `:latest`?

<details>
<summary>Answer</summary>

`:latest` is a moving target — it points to *whatever built most recently*, so it
can't tell you (or a rollback) which code is actually running. A `:${SHA}` tag is
**immutable and traceable**: it maps a running image to an exact commit, which is
what you need to debug prod or redeploy a known-good build.

</details>

**→ Next: [03-2 · Docker build & registry](02_docker_build_and_registry.md)**
