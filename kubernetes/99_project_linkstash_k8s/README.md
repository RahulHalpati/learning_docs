# 99 · Capstone — linkstash on Kubernetes

The `linkstash` app deployed to a real (local) Kubernetes cluster: a Deployment of
2 self-healing pods, a ConfigMap, and a Service, plus a Helm chart. Runs on **kind**
— no cloud.

```
kind cluster → load image → apply manifests → 2/2 pods behind a Service → /health + /shorten
```

---

## Layout

```
99_project_linkstash_k8s/
├── manifests/               # applied in order (kubectl apply -f manifests/)
│   ├── 00-namespace.yaml
│   ├── 10-configmap.yaml    # HOST / PORT
│   ├── 20-deployment.yaml   # 2 replicas + probes + resources
│   └── 30-service.yaml      # ClusterIP
├── helm/linkstash/          # the same app as a Helm chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/deployment.yaml
└── Makefile                 # cluster / image / load / deploy / verify / status / restart / delete
```

---

## Quick start

```bash
make cluster      # kind create cluster
make image load   # build linkstash:local (CI/CD course) + load into the cluster
make deploy       # kubectl apply manifests/, wait for rollout
make verify       # port-forward + curl /health
make status       # pods / deployment / service
make restart      # rolling restart (zero downtime)
make cluster-down # delete the cluster
```

### Verified output (2026-07-16 · kind v0.27.0, kubectl v1.36.2, Helm v3.16.4)

```
$ kubectl apply -f manifests/
namespace/linkstash created
configmap/linkstash-config created
deployment.apps/linkstash created
service/linkstash created
$ kubectl -n linkstash rollout status deploy/linkstash
deployment "linkstash" successfully rolled out

$ kubectl -n linkstash get deploy
NAME        READY   UP-TO-DATE   AVAILABLE
linkstash   2/2     2            2

$ curl .../health          → {"status":"ok","version":"1.2.0"}
$ curl -X POST .../shorten → {"slug":"3kcnj0","url":"https://example.com"}

$ kubectl -n linkstash scale deploy/linkstash --replicas=3   → pod count: 3
$ kubectl -n linkstash rollout restart deploy/linkstash      → successfully rolled out
$ helm lint ./helm/linkstash                                  → 0 chart(s) failed
$ helm install ls-helm ./helm/linkstash -n helm-demo          → STATUS: deployed
```

---

## What it demonstrates

| Concept | Where |
|---|---|
| Namespace, ConfigMap, Deployment, Service | `manifests/` |
| Self-healing (2 replicas) + rolling updates | `20-deployment.yaml` |
| Readiness/liveness probes on `/health` | `20-deployment.yaml` |
| Resource requests/limits | `20-deployment.yaml` |
| Manifest apply-ordering (numeric prefixes) | `manifests/00-…30-` |
| Helm templating + per-env values | `helm/linkstash/` |

---

## Two real gotchas this capstone caught

1. **Apply ordering** — `kubectl apply -f manifests/` is alphabetical, so
   `configmap`/`deployment` failed with `namespace not found` until the files were
   prefixed `00-`/`10-`/… so the namespace applies first.
2. **port-forward on a busy port** — a host port already in use made the forward
   silently fail and curl hit an unrelated local app; a free port + reading the
   `Forwarding from …` line fixed it.

---

## To the cloud

The manifests are identical for a managed cluster (EKS/GKE/AKS) — you'd provision
the cluster with **[OpenTofu](../../opentofu_iac/)**, push the image to a registry
in **[CI/CD](../../cicd_github_actions/)**, and roll out via **GitOps** ([04-3](../04_production/03_gitops_and_best_practices.md)).
Only the cluster changes; the YAML doesn't.

→ Course starts at the **[README](../README.md)** → **[00 · Introduction](../00_introduction.md)**.
