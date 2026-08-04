# 04-1 · Environments, secrets & OIDC

> **Level:** Intermediate · **Prerequisites:** [03-2 Docker build & registry](../03_build_and_artifacts/02_docker_build_and_registry.md)
> **Time:** 25 min · **Verified:** 2026-07-16

Deploying means handling credentials and targeting real environments. GitHub gives
you three tools: **secrets**, **variables**, and **environments** — plus **OIDC**
to avoid long-lived cloud keys entirely.

---

## Secrets vs variables

| | Secrets | Variables |
|---|---|---|
| For | passwords, tokens, keys | non-sensitive config (URLs, flags) |
| In logs | **masked** | visible |
| Read as | `${{ secrets.NAME }}` | `${{ vars.NAME }}` |

```yaml
- run: ./deploy.sh --token "${{ secrets.DEPLOY_TOKEN }}" --url "${{ vars.STAGING_URL }}"
```

**Never** `echo` a secret or put one in plain workflow text. GitHub masks known
secret values in logs, but a secret you construct/transform can leak — handle with
care.

---

## Environments: scoped config + protection rules

A GitHub **Environment** (Settings → Environments) is a named deploy target
(`staging`, `production`) with its **own** secrets/variables **and protection
rules**. A job opts in with `environment:`:

```yaml
  deploy-production:
    runs-on: ubuntu-latest
    environment: production          # uses production's secrets/vars + rules
    steps:
      - run: ./scripts/deploy.sh production "${{ needs.build-and-push.outputs.image }}"
```

The powerful part is the **protection rules** on `production`:

- **Required reviewers** — the job *pauses* until a human approves. This is your
  manual production gate ([04-2](02_deployment_strategies.md)) — configured in the
  UI, zero workflow code.
- **Wait timer** — force a delay before deploy.
- **Deployment branches** — only `main` may deploy to production.

Same `STAGING_URL`/`DEPLOY_TOKEN` names resolve to **different values** per
environment — so one workflow deploys to both without hardcoding anything.

---

## OIDC: stop storing cloud keys

The old way: create a cloud access key, paste it into GitHub secrets, rotate it
forever, pray it doesn't leak. **OIDC** (OpenID Connect) replaces that: GitHub
mints a short-lived, signed token proving "this is workflow X on repo Y, branch
main," and your cloud trusts it directly — **no stored long-lived key**.

```yaml
    permissions:
      id-token: write            # allow GitHub to mint the OIDC token
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/github-deploy
          aws-region: us-east-1
      # now AWS CLI calls are authenticated — nothing secret was stored
```

The cloud role's trust policy pins the exact repo/branch, so only your pipeline can
assume it. Every major cloud supports this (AWS/GCP/Azure). It's the modern
default: **keyless, short-lived, auditable.**

---

## Recap & next

- ✅ **Secrets** (masked) for credentials, **variables** for config; never echo a
  secret.
- ✅ **Environments** give per-target secrets **and protection rules** — including
  the **required-reviewer** production gate, configured in the UI.
- ✅ **OIDC** replaces stored cloud keys with short-lived, per-run tokens
  (`id-token: write`) — keyless and auditable.

**Self-check:** How does one `deploy.sh "$DEPLOY_TOKEN" "$URL"` step deploy to
*staging* in one job and *production* in another without any hardcoded values?

<details>
<summary>Answer</summary>

Each job declares a different `environment:` (`staging` vs `production`), and each
environment defines its **own** `DEPLOY_TOKEN`/`URL`. The `${{ secrets.* }}` /
`${{ vars.* }}` references resolve to the values of *that job's* environment — so
identical workflow code targets different places.

</details>

**→ Next: [04-2 · Deployment strategies](02_deployment_strategies.md)**
