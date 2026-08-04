# 03-2 · Docker build & registry

> **Level:** Intermediate · **Prerequisites:** [03-1 Artifacts & versioning](01_artifacts_and_versioning.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (Docker 29.6.1 — image built locally)

The deployable artifact for a web app is usually a **container image**. This stage
builds it and pushes it to a registry so the deploy stage can pull it. (The
[Docker course](../../docker/) covers image internals; here it's a pipeline stage.)

---

## The image (multi-stage, non-root)

[`Dockerfile`](../99_project_cicd_pipeline/Dockerfile) uses a builder stage for
dependencies and a slim runtime stage that copies only what's needed:

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /venv && /venv/bin/pip install -r requirements.txt

FROM python:3.11-slim AS runtime
ENV PATH="/venv/bin:$PATH"
COPY --from=builder /venv /venv
COPY app ./app
RUN useradd --create-home appuser
USER appuser                     # never run as root
EXPOSE 8000
CMD ["python", "-m", "app.main"]
```

Multi-stage keeps build tools out of the final image (smaller, less attack
surface); `USER appuser` drops root. Build and run it locally — verified:

```bash
$ docker build -t linkstash:local .
 => naming to docker.io/library/linkstash:local          # build succeeded
$ docker run -d -p 8011:8000 linkstash:local
$ ./scripts/smoke_test.sh http://127.0.0.1:8011
✅ smoke test passed
```

> ⚠️ Real bug caught while verifying this course: the app first bound to
> `127.0.0.1` inside the container, so the published port couldn't reach it. The
> fix — bind `0.0.0.0` in the container — is exactly the kind of thing a **smoke
> test catches** ([04-2](../04_delivery_and_deployment/02_deployment_strategies.md)).
> A green build is not a working deploy.

---

## Build & push in CI (GHCR)

From [`cd.yml`](../99_project_cicd_pipeline/.github/workflows/cd.yml) — build once,
tag with SHA + `latest`, push to **GitHub Container Registry**:

```yaml
    permissions:
      contents: read
      packages: write                       # required to push to GHCR
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}   # auto-provided; no PAT needed
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha             # reuse layers across runs
          cache-to: type=gha,mode=max
```

Three things worth noting:

- **`secrets.GITHUB_TOKEN`** is injected automatically — with `packages: write` it
  can push to your repo's GHCR. No personal access token to manage.
- **`cache-from/to: type=gha`** caches Docker layers in GitHub's cache, so
  unchanged layers aren't rebuilt — often the biggest CI speedup for image builds.
- **Registry choice** is yours: GHCR (shown, integrates with the repo), Docker Hub,
  or a cloud registry (ECR/GAR). The workflow is the same; only login differs.

---

## Recap & next

- ✅ Package the app as a **multi-stage, non-root image**; build once and push to a
  **registry** (GHCR here).
- ✅ Use `secrets.GITHUB_TOKEN` + `packages: write` (no PAT) and **`type=gha` layer
  caching** for speed.
- ✅ A green build ≠ a working deploy — the container smoke test caught a real
  bind-address bug.

**Self-check:** The `docker/login-action` uses `secrets.GITHUB_TOKEN` with
`permissions: packages: write`. Why is that better than creating a personal access
token and storing it as a secret?

<details>
<summary>Answer</summary>

`GITHUB_TOKEN` is **auto-generated per run, scoped by `permissions:`, and expires
when the run ends** — nothing to create, rotate, or leak. A personal access token
is long-lived, broadly scoped, and a manual secret you must manage and could leak.
Least privilege + no maintenance.

</details>

**→ Next: [04-1 · Environments, secrets & OIDC](../04_delivery_and_deployment/01_environments_secrets_oidc.md)**
