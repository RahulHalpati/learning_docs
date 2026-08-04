# 04-3 · Releases & versioning

> **Level:** Intermediate · **Prerequisites:** [04-2 Deployment strategies](02_deployment_strategies.md)
> **Time:** 20 min · **Verified:** 2026-07-16

Beyond continuous deploys, you often want **named, versioned releases** — a
`v1.2.0` with an immutable image and a changelog. A tag triggers it.

---

## Tag-triggered releases

Push a version tag and the release workflow fires:

```bash
git tag v1.2.0
git push origin v1.2.0
```

[`release.yml`](../99_project_cicd_pipeline/.github/workflows/release.yml):

```yaml
on:
  push:
    tags: ["v*"]

permissions:
  contents: write        # to create the GitHub Release
  packages: write        # to push the versioned image

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}   # e.g. :v1.2.0
      - uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true       # auto-changelog from merged PRs
```

`github.ref_name` is the tag (`v1.2.0`), so the image is tagged with the exact
version. `generate_release_notes: true` writes the changelog from PRs merged since
the last tag — free release notes.

---

## Keep the version in sync

The tag, the image tag, and the app's reported version should agree. `linkstash`
declares `__version__ = "1.2.0"` (in `app/__init__.py` and `pyproject.toml`) and
serves it at `/health` — so after releasing `v1.2.0` you can confirm:

```bash
curl -s https://.../health   # {"status":"ok","version":"1.2.0"}
```

A mismatch (tag says 1.2.0, `/health` says 1.1.0) means the wrong build shipped —
worth a smoke-test assertion.

---

## Automating the version bump

Bumping the version by hand is easy to forget. Tools that automate it from commit
messages:

- **Conventional Commits** — `feat:` / `fix:` / `feat!:` prefixes encode the bump.
- **semantic-release** / **release-please** — read those commits, compute the next
  semver, tag, and generate the changelog automatically.

Adopt these once manual tagging gets tedious; the tag-triggered workflow above
doesn't change — the tag just gets created for you.

---

## Recap & next

- ✅ A **`v*` tag** triggers a release: build a **version-tagged image** + a GitHub
  Release with **auto-generated notes**.
- ✅ Keep tag ↔ image ↔ `/health` version **in sync**; a mismatch means the wrong
  build shipped.
- ✅ Automate bumps with **Conventional Commits + semantic-release** when manual
  tagging gets old.

**Self-check:** After `git push origin v1.2.0`, which workflow runs — `ci.yml`,
`cd.yml`, or `release.yml` — and why?

<details>
<summary>Answer</summary>

`release.yml`, because it's the one triggered by `on: push: tags: ["v*"]`. `ci.yml`
runs on branch pushes/PRs and `cd.yml` runs after CI completes on `main` — neither
is triggered by a tag push. (A tag push doesn't move `main`, so CD's `workflow_run`
on main doesn't fire.)

</details>

**→ Next: [05-1 · Reusable workflows & composite actions](../05_advanced_and_shipping/01_reusable_workflows.md)**
