# 04-2 · Observability & troubleshooting

> **Level:** Intermediate · **Prerequisites:** [04-1 Packaging with Helm](01_helm.md)
> **Time:** 20 min · **Verified:** 2026-07-16

Something's wrong with a pod. Kubernetes tells you exactly what — if you know the
four commands to ask. This is the debugging loop you'll use most.

---

## The debug loop

```mermaid
flowchart LR
    G[get pods<br/>what state?] --> D[describe pod<br/>why? events] --> L[logs<br/>app said what?] --> E[exec<br/>poke inside]
```

### 1. `get` — what state is it in?

```bash
kubectl -n linkstash get pods
```

The **STATUS** column is your first clue. Common non-`Running` states:

| STATUS | Usually means |
|---|---|
| `Pending` | can't be scheduled (no node has the requested resources) |
| `ImagePullBackOff` | can't pull the image (wrong name/tag, or not loaded into kind) |
| `CrashLoopBackOff` | container starts then exits repeatedly (app error, or liveness probe) |
| `Running` but `0/1` READY | **readiness** probe failing — up but not taking traffic |

### 2. `describe` — why? (read the Events)

```bash
kubectl -n linkstash describe pod <pod>
```

Scroll to **Events** at the bottom — the timeline of what Kubernetes tried:
`Scheduled`, `Pulled`, `Started`, or failures like `Failed to pull image` /
`Liveness probe failed`. **This is the single most useful debug command.**

### 3. `logs` — what did the app say?

```bash
kubectl -n linkstash logs deploy/linkstash          # current logs
kubectl -n linkstash logs <pod> --previous          # the crashed container's logs
kubectl -n linkstash logs -f deploy/linkstash       # follow live
```

Verified on the running app:

```
 * Serving Flask app 'main'
```

`--previous` is the trick for `CrashLoopBackOff` — it shows the logs of the *dead*
container, which is where the error actually is.

### 4. `exec` — get inside

```bash
kubectl -n linkstash exec -it <pod> -- sh
# now you're in the container: check env, hit localhost:8000, inspect files
```

---

## A diagnosis cheat-sheet

| Symptom | First check |
|---|---|
| `ImagePullBackOff` | image name/tag; on kind, did you `kind load docker-image`? |
| `CrashLoopBackOff` | `logs --previous` — the app is erroring on startup |
| `Pending` forever | `describe` → Events: insufficient CPU/memory (lower requests or add nodes) |
| `Running` 0/1 ready | readiness probe path/port; `describe` shows probe failures |
| Service times out | `get endpoints <svc>` empty → selector/label mismatch ([01-4](../01_foundations/04_services_and_networking.md)) |

---

## Beyond the built-ins

`kubectl` gets you far, but production adds: **metrics-server** (`kubectl top pods`
for live CPU/memory), **Prometheus + Grafana** (metrics/dashboards/alerts), and a
log aggregator (**Loki**, ELK) so you're not `kubectl logs`-ing across dozens of
pods. Same signals you'd wire in the [CI/CD](../../cicd_github_actions/) and
[LLMOps] observability lessons — centralised instead of per-pod.

---

## Recap & next

- ✅ The debug loop is **get → describe (Events!) → logs → exec**; STATUS is your
  first clue.
- ✅ **`describe` Events** and **`logs --previous`** are the two highest-value moves
  (why it won't start; what the crashed container said).
- ✅ Production centralises signals with **metrics-server, Prometheus/Grafana, and
  log aggregation**.

## Exercise

A pod is stuck in `CrashLoopBackOff`. Which single command most likely shows you
the actual cause, and why not plain `kubectl logs`?

<details>
<summary>Answer</summary>

`kubectl logs <pod> --previous`. In `CrashLoopBackOff` the current container has
already died and a new one may not be up, so plain `kubectl logs` shows nothing (or
the fresh attempt). `--previous` prints the **crashed** container's logs — where the
startup error actually is. Pair it with `describe` to see the restart Events.

</details>

**→ Next: [04-3 · GitOps, RBAC & best practices](03_gitops_and_best_practices.md)**
