# 05-1 · Reusable workflows & composite actions

> **Level:** Advanced · **Prerequisites:** [04-3 Releases & versioning](../04_delivery_and_deployment/03_release_and_versioning.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (workflow syntax)

Once you have more than one repo (or one workflow with repeated blocks), you'll
copy-paste YAML — and copy-pasted YAML drifts. Two features fix that: **reusable
workflows** and **composite actions**.

---

## The duplication problem

Every repo's CI does roughly the same thing: checkout, set up Python, install,
lint, test. Copy that into ten repos and a fix (say, bumping `setup-python@v5→v6`)
means ten edits. DRY applies to pipelines too.

---

## Composite actions: bundle repeated *steps*

A **composite action** packages a sequence of steps behind one `uses:`. Put shared
setup in `.github/actions/setup/action.yml`:

```yaml
# .github/actions/setup/action.yml
name: setup
description: Checkout + Python + deps
runs:
  using: composite
  steps:
    - uses: actions/setup-python@v5
      with: { python-version: "3.11", cache: pip }
    - run: pip install -r requirements-dev.txt
      shell: bash        # composite run-steps must name a shell
```

Then every job collapses to:

```yaml
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup       # the composite action
      - run: ruff check app tests
```

Best for **repeated steps within** your workflows.

---

## Reusable workflows: share a whole *job*

A **reusable workflow** is a full workflow another workflow can `call`, passing
inputs/secrets. Define it with `on: workflow_call`:

```yaml
# .github/workflows/reusable-ci.yml
on:
  workflow_call:
    inputs:
      python-version: { type: string, default: "3.11" }

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ inputs.python-version }} }
      - run: pip install -r requirements-dev.txt && make ci
```

Call it from any repo:

```yaml
# .github/workflows/ci.yml in any repo
jobs:
  ci:
    uses: my-org/.github/.github/workflows/reusable-ci.yml@v1
    with: { python-version: "3.12" }
```

Now the pipeline lives in **one place**; every repo references it by version. Fix
it once, everyone benefits.

| Feature | Shares | Reach for when |
|---|---|---|
| **Composite action** | a sequence of **steps** | repeated setup within your workflows |
| **Reusable workflow** | a whole **job/workflow** | standardising CI across many repos |

---

## Matrix + reusable = org-wide standard

Combine them: a reusable workflow with a matrix becomes your organisation's
canonical "how we test Python services," referenced by tag (`@v1`) so changes roll
out deliberately. This is how platform teams give dozens of repos a consistent,
maintained pipeline without copy-paste.

---

## Recap & next

- ✅ **Composite actions** bundle repeated **steps**; **reusable workflows** share a
  whole **job/workflow** via `workflow_call`.
- ✅ Reference reusable workflows **by version tag** so the pipeline lives in one
  place and updates roll out on purpose.
- ✅ Together they make one **org-wide standard pipeline** instead of N drifting
  copies.

**Self-check:** You want ten repos to share the *entire* CI pipeline, updated
centrally. Composite action or reusable workflow?

<details>
<summary>Answer</summary>

A **reusable workflow** (`on: workflow_call`), referenced as
`uses: org/repo/.github/workflows/ci.yml@v1`. A composite action only bundles
steps *inside* a job you still have to define in each repo; a reusable workflow
provides the whole job/pipeline centrally.

</details>

**→ Next: [05-2 · Hardening, gates & DORA](02_hardening_gates_and_dora.md)**
