# 03-2 · Apply & verify

> **Level:** Intermediate · **Prerequisites:** [03-1 The manifests](01_the_manifests.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (full run)

The moment of truth: get the image into the cluster, apply the manifests, and
confirm real traffic reaches the app. This whole sequence was executed for this
course — every block below is real output.

---

## 1. Get the image into the cluster

kind has no registry, so load the locally-built image directly into the cluster's
nodes:

```bash
docker build --load -t linkstash:local ../../cicd_github_actions/99_project_cicd_pipeline
kind load docker-image linkstash:local --name learn
```

```
Image: "linkstash:local" ... not yet present on node "learn-control-plane", loading...
```

(In a real cluster you'd `docker push` to a registry — GHCR from the
[CI/CD course](../../cicd_github_actions/03_build_and_artifacts/02_docker_build_and_registry.md) —
and the nodes would pull it. `kind load` is the local shortcut.)

---

## 2. Apply

```bash
kubectl apply -f manifests/
```

```
namespace/linkstash created
configmap/linkstash-config created
deployment.apps/linkstash created
service/linkstash created
```

```bash
kubectl -n linkstash rollout status deploy/linkstash
```

```
Waiting for deployment "linkstash" rollout to finish: 1 of 2 updated replicas are available...
deployment "linkstash" successfully rolled out
```

---

## 3. Look at what's running

```bash
kubectl -n linkstash get pods,deploy,svc
```

```
NAME                             READY   STATUS    RESTARTS   AGE
pod/linkstash-6795fdd8dc-fpmzw   1/1     Running   0          17s
pod/linkstash-6795fdd8dc-q2hkr   1/1     Running   0          17s

NAME                        READY   UP-TO-DATE   AVAILABLE
deployment.apps/linkstash   2/2     2            2

NAME                TYPE        CLUSTER-IP     PORT(S)   AGE
service/linkstash   ClusterIP   10.96.104.99   80/TCP    17s
```

Two pods `Running`, deployment `2/2`, a Service with a ClusterIP. The app is live
*inside* the cluster.

---

## 4. Verify real traffic

ClusterIP is internal, so `port-forward` from your laptop (use a **free** port):

```bash
kubectl -n linkstash port-forward svc/linkstash 18899:80
# Forwarding from 127.0.0.1:18899 -> 8000
```

```bash
curl http://127.0.0.1:18899/health
# {"status":"ok","version":"1.2.0"}
curl -X POST http://127.0.0.1:18899/shorten -H 'Content-Type: application/json' -d '{"url":"https://example.com"}'
# {"slug":"3kcnj0","url":"https://example.com"}
```

Traffic went **laptop → Service → one of the two pods → the app**. `POST /shorten`
returning a slug proves the real app is serving, not just that pods exist.

> ⚠️ Verifying this course, the first port-forward used a port already taken on the
> host, silently failed, and curl hit an *unrelated* local app (a different
> `/health`). The fix — a free port, and reading the port-forward log line
> `Forwarding from 127.0.0.1:18899 -> 8000` — is a lesson in itself: **confirm the
> forward is established before trusting the curl.**

---

## 5. `make` wraps the whole thing

The capstone [`Makefile`](../99_project_linkstash_k8s/Makefile) is the one-liner
version of all of the above:

```bash
make cluster image load deploy verify status
```

Same commands you'd run by hand, in one place — the local-mirror idea from the
CI/CD course, applied to Kubernetes.

---

## Recap & next

- ✅ **`kind load docker-image`** puts the local image on the cluster (no registry);
  production uses `docker push` + a pull.
- ✅ **apply → rollout status → get pods/svc** confirms 2/2 pods behind a ClusterIP.
- ✅ **`port-forward` + curl** proves real traffic reaches the app (`/health` 1.2.0,
  `/shorten` returns a slug) — verify the forward is up first.

## Exercise

After deploying, run `kubectl -n linkstash delete pod <one-pod>` while curling
`/health` in a loop through the port-forward. What do you observe, and why does the
app stay available?

<details>
<summary>Answer</summary>

The deleted pod is replaced within seconds (self-healing), and `/health` keeps
returning `200` throughout — because the **Service** still has the *other* ready
pod and routes only to ready endpoints. With 2 replicas, losing one never drops to
zero capacity. That's the whole point of running more than one pod behind a Service.

</details>

**→ Next: [04-1 · Packaging with Helm](../04_production/01_helm.md)**
