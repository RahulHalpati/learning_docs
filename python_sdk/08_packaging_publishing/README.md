# Section 08 · Packaging & publishing ⭐

> **Prerequisites:** [Section 02 · Packaging basics](../02_packaging_basics/README.md) and the finished [capstone](../99_project_pokesdk/README.md). You don't strictly need Sections 03–07 for the mechanics, but you'll publish the SDK you built there.
> **Time:** ~4–6 hours.

Section 02 made the SDK *installable on your machine*. This section makes it **installable by anyone, anywhere** — the part that turns "I wrote a library" into "I shipped a library." You'll fill out the package metadata that appears on PyPI, adopt **semantic versioning** and a changelog so upgrades are safe, build proper **wheels and sdists**, publish to **TestPyPI then PyPI**, and automate the whole release with a **GitHub Actions** workflow using trusted publishing. Everything here was run end-to-end: real `build`, real `twine check`, real metadata.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [Metadata & dependencies](01_pyproject_metadata_deps.md) | What goes in `pyproject.toml` for a real PyPI release? |
| 02 | [Versioning & changelog](02_versioning_and_changelog.md) | How do I version so upgrades don't break users? |
| 03 | [Building wheels & sdists](03_building_wheels.md) | How do I turn the project into uploadable artifacts? |
| 04 | [Publishing to PyPI](04_publishing_to_pypi.md) | How do I actually upload it (safely, TestPyPI first)? |
| 05 | [CI with GitHub Actions](05_ci_github_actions.md) | How do I test on every push and release automatically? |

## What you'll be able to do after this section

- Write complete, correct `pyproject.toml` metadata (classifiers, URLs, extras, data files like `py.typed`).
- Apply semantic versioning, keep a changelog, and manage a single source of version truth.
- Build wheels + sdists with `build` (and `uv`), and verify their contents and metadata.
- Publish to TestPyPI and PyPI with `twine`, using API tokens or trusted publishing.
- Set up CI that runs your tests on every push and publishes on a tagged release — no secrets to leak.

→ Start: **[01 · Metadata & dependencies](01_pyproject_metadata_deps.md)**
