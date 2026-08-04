# 01-2 · Setup: kind & kubectl

> **Level:** Intermediate · **Prerequisites:** [01-1 What is Kubernetes?](01_what_is_kubernetes.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (kind v0.27.0, kubectl v1.36.2)

Two tools: **kind** runs a cluster inside Docker; **kubectl** is how you talk to
any cluster. Install both, create a cluster, learn the handful of commands you'll
use constantly.

---

## Install

```bash
# kubectl — the Kubernetes CLI
curl -fsSLo ~/.local/bin/kubectl "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ~/.local/bin/kubectl

# kind — Kubernetes IN Docker
curl -fsSLo ~/.local/bin/kind https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-amd64
chmod +x ~/.local/bin/kind
```

(Docker must be running — kind builds the cluster out of containers.)

---

## Create a cluster

```bash
kind create cluster --name learn
```

Verified:

```
 ✓ Preparing nodes 📦
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
Set kubectl context to "kind-learn"
```

kind wires `kubectl` to the new cluster automatically (the **context**
`kind-learn`). Confirm:

```bash
kubectl cluster-info
# Kubernetes control plane is running at https://127.0.0.1:39675
kubectl get nodes
# NAME                 STATUS   ROLES           AGE   VERSION
# learn-control-plane  Ready    control-plane   ...   v1.xx
```

---

## The kubectl commands you'll use all day

`kubectl <verb> <resource>` — a handful cover 90% of the work:

| Command | Does |
|---|---|
| `kubectl get pods` | list resources (add `-A` for all namespaces, `-o wide`) |
| `kubectl apply -f file.yaml` | create/update from a manifest (declarative) |
| `kubectl describe pod X` | detailed status + recent **events** (your #1 debug tool) |
| `kubectl logs X` | container logs (`-f` to follow) |
| `kubectl exec -it X -- sh` | a shell inside a running container |
| `kubectl delete -f file.yaml` | remove what the manifest created |
| `kubectl -n NS ...` | scope to a namespace |

**`apply` is the one to internalise:** it's declarative — you edit the YAML and
re-`apply`, and Kubernetes computes the diff. You rarely use imperative `create`.

---

## Namespaces & context

- **Namespace** — a scope. `kubectl get pods -n linkstash` looks only in that
  namespace. Set a default with `kubectl config set-context --current --namespace=linkstash`.
- **Context** — which cluster/user/namespace `kubectl` points at. `kubectl config
  get-contexts` lists them; `kubectl config use-context kind-learn` switches. This
  is how one `kubectl` manages many clusters (local, staging, prod) — check your
  context before you run anything destructive.

---

## Tear down

```bash
kind delete cluster --name learn
```

Instant and total — the whole cluster was containers. This throwaway nature is why
kind is perfect for learning and CI: break it, delete it, recreate in a minute.

---

## Recap & next

- ✅ **kind** creates a real cluster inside Docker; **kubectl** drives any cluster
  via its **context**.
- ✅ Core verbs: **`get` / `apply` / `describe` / `logs` / `exec` / `delete`**, scoped
  with **`-n`**; `apply` is declarative.
- ✅ Check your **context** before acting; delete a kind cluster in one command.

**Self-check:** You run `kubectl get pods` and see "No resources found in default
namespace," but you know linkstash is deployed. What happened?

<details>
<summary>Answer</summary>

Your pods are in the **`linkstash` namespace**, not `default`. `kubectl get pods`
only shows the current namespace. Use `kubectl get pods -n linkstash` (or
`-A` for all namespaces, or set your default namespace). Forgetting the namespace
is the most common early confusion.

</details>

**→ Next: [01-3 · Pods & Deployments](03_pods_and_deployments.md)**
