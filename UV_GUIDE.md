# 📦 uv in one hour

> **Honest framing first:** uv **will not get you hired**. No interviewer has ever rejected a candidate for using `venv` + `pip`, and none will hire you for using uv. It's a *quality-of-life and reproducibility* tool — you learn it in an hour, use it daily, and never think about it again. Learn it because installs drop from 40 s to 2 s, not because it's a résumé line.
>
> **What *is* worth being able to explain in an interview:** why a **lockfile** matters (see [§4](#4--the-one-idea-that-matters-lockfiles)). That answer is the same whether you use uv, Poetry, or pip-tools.
>
> **Time:** ~1 h (30 min reading, 30 min doing). **Prerequisite:** you already understand `venv` and `pip`.

---

## 1 · What it is

A single Rust binary from Astral (the `ruff` team) that replaces **pip + venv + pyenv + pip-tools + pipx**. It's 10–100× faster because it's compiled, aggressively parallel, and caches globally with hardlinks instead of re-downloading and re-copying wheels per project.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # installs to ~/.local/bin
uv --version
```
No Python needed to install it — uv can install Python itself.

---

## 2 · Path A — uv as "fast pip" (zero new concepts)

Start here. **Nothing about your workflow changes**, it just gets fast. Use this on existing projects today.

```bash
uv venv                              # ≈ python -m venv .venv  (also picks a Python for you)
source .venv/bin/activate            # exactly as before
uv pip install fastapi               # ≈ pip install
uv pip install -r requirements.txt   # ≈ pip install -r
uv pip freeze > requirements.txt     # ≈ pip freeze
uv pip uninstall fastapi
uv pip list
```

`uv pip` is a **pip-compatible interface**, not pip. Same flags you know, same `requirements.txt`, same activated-venv mental model.

> If you stop reading here you've already got 90% of the daily benefit.

---

## 3 · Path B — the project workflow (what modern repos use)

For **new** projects. Instead of a hand-maintained `requirements.txt`, uv manages a `pyproject.toml` + a real lockfile.

```bash
uv init myapi && cd myapi     # creates pyproject.toml, .python-version, README, main.py
uv add fastapi uvicorn        # installs + records in pyproject.toml + updates uv.lock
uv add --dev pytest ruff      # dev-only dependency group
uv remove uvicorn
uv sync                       # make the env exactly match uv.lock
uv run pytest                 # run inside the env — NO activation needed
uv run uvicorn app.main:app --reload
uv lock --upgrade             # deliberately bump the lockfile
uv tree                       # see the dependency tree
```

What `uv init` gives you:

```
myapi/
├── pyproject.toml      # your declared dependencies (what you asked for)
├── uv.lock             # the exact resolved versions + hashes (what you got)  ← commit this
├── .python-version     # the Python version for this project
└── .venv/              # created automatically; gitignore it
```

```toml
# pyproject.toml
[project]
name = "myapi"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.116", "uvicorn>=0.30"]

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6"]
```

**`uv run` is the habit change worth making.** It syncs the env if needed, then runs the command — so "did I activate the right venv?" stops being a question you ever ask.

### Python versions (replaces pyenv)
```bash
uv python install 3.12      # download a Python
uv python list              # what's available/installed
uv python pin 3.12          # write .python-version for this project
```

### One-off tools (replaces pipx)
```bash
uvx ruff check .            # run a tool without installing it into your project
uv tool install ruff        # install a tool globally
```

---

## 4 · The one idea that matters: lockfiles

This is the part worth understanding, independent of uv.

| | `pip freeze > requirements.txt` | `uv.lock` |
|---|---|---|
| Records | what's installed **on your machine right now** | the full resolved graph |
| Hashes | ❌ no | ✅ yes (supply-chain integrity) |
| Cross-platform | ❌ it's your OS/Python's resolution | ✅ resolves for multiple platforms |
| Direct vs transitive | ⚠️ flattened — you can't tell | ✅ separated (pyproject = intent, lock = result) |
| Reproducible in CI | mostly, by luck | **by construction** |

Two files, two jobs: **`pyproject.toml` = what you asked for. `uv.lock` = exactly what you got.** Commit both. That's what kills "works on my machine."

**Rule:** commit `uv.lock` for applications and services. For a *library* you publish, keep it for your own CI but let consumers resolve their own versions.

---

## 5 · CI and Docker (where it actually pays)

CI install time drops from minutes to seconds, and `--frozen` guarantees the lockfile is respected.

```yaml
# GitHub Actions
- uses: astral-sh/setup-uv@v5
  with: { enable-cache: true }
- run: uv sync --frozen          # fails if uv.lock is out of date — that's the point
- run: uv run pytest
```

```dockerfile
# multi-stage: deps resolved in the builder, only the venv ships
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./          # copy manifests FIRST for layer caching
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app .
ENV PATH="/app/.venv/bin:$PATH"         # now `python`/`uvicorn` resolve to the venv
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Flags that matter: `--frozen` (don't touch the lock — CI/prod), `--no-dev` (skip dev group), `--no-install-project` (deps only, for cache layering).

---

## 6 · Gotchas

- **`uv pip install` needs an activated venv** (or `--python`), same as pip. `uv add`/`uv sync` manage `.venv` for you and don't need activation.
- **Don't mix the two paths in one project.** Either `requirements.txt` + `uv pip`, or `pyproject.toml` + `uv add`. Mixing means the lockfile lies.
- **uv's resolver is stricter than old pip.** If it errors where pip didn't, it usually found a real conflict pip was silently ignoring. Read the message before forcing anything.
- **Follow your team's standard.** Don't convert a shared repo's tooling unilaterally — that's a discussion, not a commit. But `uv pip` works fine against an existing `requirements.txt` with no repo changes at all, so you can be fast without changing anything for anyone else.
- `.venv/` in `.gitignore`; `uv.lock` **not** in `.gitignore`.

---

## 7 · Command translation

| pip / venv / pyenv / pipx | uv |
|---|---|
| `python -m venv .venv` | `uv venv` |
| `pip install X` | `uv pip install X` · `uv add X` |
| `pip install -r requirements.txt` | `uv pip install -r requirements.txt` · `uv sync` |
| `pip freeze > requirements.txt` | `uv pip freeze > requirements.txt` · (or just commit `uv.lock`) |
| `pip uninstall X` | `uv pip uninstall X` · `uv remove X` |
| `pip list` / `pipdeptree` | `uv pip list` / `uv tree` |
| `python script.py` (after activating) | `uv run script.py` |
| `pyenv install 3.12` | `uv python install 3.12` |
| `pipx run ruff` | `uvx ruff` |
| `python -m build` / `twine upload` | `uv build` / `uv publish` |

---

## 8 · Practice (30 min, do it now)

```bash
# 1. New project, real deps, run it
uv init uvdemo && cd uvdemo
uv add fastapi uvicorn
uv add --dev pytest ruff
cat pyproject.toml            # see your intent
head -30 uv.lock              # see the resolved result + hashes

# 2. Prove reproducibility
rm -rf .venv && uv sync       # rebuilt from the lockfile — time it
uv run python -c "import fastapi; print(fastapi.__version__)"

# 3. Prove --frozen does its job
uv add httpx --frozen         # should refuse: lock would need to change
uv add httpx                  # works, lock updated

# 4. Convert an existing project non-destructively
cd ~/some-old-project
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt    # time it vs pip. That's the whole pitch.
```

If all four worked, you're done. That's uv.

---

## 9 · So should you switch?

**Yes — incrementally, and for the right reason.**

- **Today:** use `uv venv` + `uv pip` everywhere. Zero risk, zero new concepts, immediate speed.
- **New projects:** use `uv init` / `uv add` / `uv run` and commit `uv.lock`. Matches this repo's courses, so commands copy-paste.
- **Shared/legacy repos:** leave the tooling alone; still use `uv pip` locally.

**Keep your venv/pip knowledge.** It's the fundamental, it's what you'll find on every existing project, and it's what an interviewer is more likely to ask about. uv is a faster front-end to the same ideas — not a replacement for understanding them.

*And to restate the top: this is an hour of tooling, not a career move. Spend the saved hours on RAG and agents.*
