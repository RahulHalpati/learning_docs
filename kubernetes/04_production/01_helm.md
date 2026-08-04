# 04-1 · Packaging with Helm

> **Level:** Intermediate · **Prerequisites:** [03-2 Apply & verify](../03_deploying_linkstash/02_apply_and_verify.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (Helm v3.16.4)

Raw manifests work, but copy-pasting them per environment drifts (the same problem
modules solved in OpenTofu). **Helm** is the package manager for Kubernetes: one
**templated chart** + per-environment **values**.

---

## A chart is templated manifests + values

The capstone's [`helm/linkstash/`](../99_project_linkstash_k8s/helm/linkstash/):

```
helm/linkstash/
├── Chart.yaml          # name, version, appVersion
├── values.yaml         # defaults (replicaCount, image, resources, env)
└── templates/
    └── deployment.yaml # manifest with {{ .Values.* }} placeholders
```

`values.yaml` holds the knobs:

```yaml
replicaCount: 2
image: { repository: linkstash, tag: local, pullPolicy: IfNotPresent }
resources:
  requests: { cpu: 50m, memory: 64Mi }
  limits:   { cpu: 250m, memory: 128Mi }
```

The template substitutes them:

```yaml
spec:
  replicas: {{ .Values.replicaCount }}
  # ...
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
```

One chart, and staging vs prod differ only by a values file — no duplicated YAML.

---

## Lint & install — verified

```bash
helm lint ./helm/linkstash
```

```
1 chart(s) linted, 0 chart(s) failed
```

```bash
helm install ls-helm ./helm/linkstash -n helm-demo --create-namespace
```

```
NAME: ls-helm
STATUS: deployed
REVISION: 1
deployment "ls-helm" successfully rolled out
```

Both were run in this course's environment. Per-environment installs:

```bash
helm install linkstash ./helm/linkstash -f values-staging.yaml -n staging --create-namespace
helm install linkstash ./helm/linkstash -f values-prod.yaml    -n prod    --create-namespace
```

---

## Releases: upgrade, rollback, uninstall

Helm tracks each install as a versioned **release**:

```bash
helm upgrade linkstash ./helm/linkstash -f values-prod.yaml   # ship a change
helm rollback linkstash 1                                      # revert to revision 1
helm list -n prod                                              # what's installed
helm uninstall linkstash -n prod                               # remove it all
```

`helm rollback` reverts the *whole release* (all its objects) to a prior revision —
a coarser, more complete rollback than `kubectl rollout undo` (which is one
Deployment). And you consume others' charts the same way (`helm install
ingress-nginx ...`), which is how you install ecosystem components.

---

## Helm vs Kustomize

The other common tool is **Kustomize** (built into kubectl: `kubectl apply -k`),
which *overlays* patches onto base manifests instead of templating. Rule of thumb:
**Kustomize** for your own app's env variations (no templating language);
**Helm** for packaging/sharing and installing third-party components. Many teams
use both.

---

## Recap & next

- ✅ A **Helm chart** = templated manifests + a **values** file; one chart deploys
  many environments without duplicated YAML.
- ✅ Verified: `helm lint` (0 failed) and `helm install` → rollout. Installs are
  versioned **releases** with `upgrade`/`rollback`/`uninstall`.
- ✅ **Kustomize** (overlays) vs **Helm** (templating/packaging) — use Helm for
  sharing and third-party components.

## Exercise

Render the chart *without* installing to inspect the generated YAML, then install
with 3 replicas instead of the default 2 — without editing `values.yaml`.

<details>
<summary>Solution</summary>

`helm template ./helm/linkstash` prints the rendered manifests (great for diffing
before an upgrade). Override a value at install time with `--set`:
`helm install linkstash ./helm/linkstash --set replicaCount=3 -n demo --create-namespace`.
`--set` (or `-f other-values.yaml`) overrides defaults without touching the chart —
the point of values.

</details>

**→ Next: [04-2 · Observability & troubleshooting](02_observability_and_troubleshooting.md)**
