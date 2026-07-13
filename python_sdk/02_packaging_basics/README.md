# Section 02 · Packaging basics

> **Prerequisites:** [Section 01 · Foundations](../01_foundations/README.md).
> **Time:** ~2–3 hours.

We fix the naive client's Problem 8 first — *it's not even installable* — because everything we build afterward needs to live in a real, importable package called `pokesdk`. This section is the skeleton: the folder layout professionals use, the one config file (`pyproject.toml`) that makes it a package, an editable install so your code is importable while you edit it, and the discipline of deciding what's **public** vs **private**.

> We do the *full* publishing story (versioning, building wheels, PyPI, CI) later in **[Section 08](../08_packaging_publishing/README.md)**, once there's a finished SDK worth shipping. This section is just enough packaging to start building.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [Project layout & the src/ directory](01_project_layout_src.md) | Where do files go, and why `src/`? |
| 02 | [pyproject.toml & editable install](02_pyproject_and_editable_install.md) | How does a folder become an importable, installable package? |
| 03 | [Imports & your public API](03_imports_and_public_api.md) | What's public, what's private, and how do users import it? |

## What you'll be able to do after this section

- Lay out a Python package with the `src/` layout and explain why it prevents a whole class of packaging bugs.
- Write a minimal `pyproject.toml` with a build backend and install your package editable (`pip install -e .`).
- Control your public API deliberately with `__init__.py`, `__all__`, and `_private` naming.

→ Start: **[01 · Project layout & the src/ directory](01_project_layout_src.md)**
