# 02-1 · ConfigMaps & Secrets

> **Level:** Intermediate · **Prerequisites:** [01-4 Services & networking](../01_foundations/04_services_and_networking.md)
> **Time:** 20 min · **Verified:** 2026-07-16

Config doesn't belong baked into the image — the same image should run in staging
and prod with different settings. **ConfigMaps** hold non-secret config; **Secrets**
hold sensitive values; both get injected into pods as env vars or files.

---

## ConfigMap → env vars

From the capstone ([`manifests/10-configmap.yaml`](../99_project_linkstash_k8s/manifests/10-configmap.yaml)):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: linkstash-config
  namespace: linkstash
data:
  HOST: "0.0.0.0"
  PORT: "8000"
```

Inject the whole ConfigMap as environment variables in the Deployment:

```yaml
      containers:
        - name: linkstash
          image: linkstash:local
          envFrom:
            - configMapRef:
                name: linkstash-config    # every key becomes an env var
```

Now the *same image* is configured per environment by swapping the ConfigMap — no
rebuild. (You can also mount a ConfigMap as files, e.g. an `nginx.conf`.)

---

## Secrets — same idea, for sensitive values

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: linkstash-secrets
  namespace: linkstash
type: Opaque
stringData:
  SECRET_KEY: "dev-secret-rotate-me"     # stringData: plaintext in, stored base64
```

```yaml
          envFrom:
            - configMapRef: { name: linkstash-config }
            - secretRef:    { name: linkstash-secrets }
```

⚠️ **Secrets are base64-encoded, not encrypted, by default** — base64 is *not*
security. So:

- Don't commit Secret manifests with real values to git.
- Enable **encryption at rest** for etcd, and lock down access with **RBAC**
  ([04-3](../04_production/03_gitops_and_best_practices.md)).
- In production, source secrets from a real manager — **External Secrets Operator**
  pulling from AWS Secrets Manager (the [LocalStack course](../../aws_localstack/05_more_services/01_secrets_and_ssm.md)
  taught that store), Vault, or the cloud's secret store.

---

## Config as a first-class concern

Notice the through-line across the collection: the [code-audit course](../../secure_code_audit/)
flagged hardcoded secrets, the [LocalStack course](../../aws_localstack/) moved them
to Secrets Manager, and here they're injected as K8s Secrets. Same principle at
every layer — **config and secrets live outside the artifact**, injected at runtime.

---

## Recap & next

- ✅ **ConfigMap** = non-secret config, **Secret** = sensitive values; inject both
  via **`envFrom`** (or mount as files) so one image runs anywhere.
- ✅ K8s **Secrets are base64, not encrypted** — use etcd encryption at rest, RBAC,
  and a real secret manager for production.
- ✅ Config/secrets belong **outside the image**, injected at runtime — the same
  principle as the audit and LocalStack courses.

**Self-check:** A teammate says "Secrets are safe because they're encoded." Correct
them in one sentence, and name one thing that actually protects a Secret.

<details>
<summary>Answer</summary>

Base64 is **encoding, not encryption** — anyone with read access can decode it
instantly (`base64 -d`). Real protection comes from **RBAC** limiting who can read
Secrets, **encryption at rest** for etcd, and sourcing values from an external
secret manager rather than storing them in the cluster/git.

</details>

**→ Next: [02-2 · Health probes & resources](02_probes_and_resources.md)**
