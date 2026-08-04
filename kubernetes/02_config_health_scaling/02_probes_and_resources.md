# 02-2 · Health probes & resources

> **Level:** Intermediate · **Prerequisites:** [02-1 ConfigMaps & Secrets](01_configmaps_and_secrets.md)
> **Time:** 25 min · **Verified:** 2026-07-16

Kubernetes can only self-heal if it knows what "healthy" means and how much a pod
is allowed to use. **Probes** define health; **requests/limits** define resources.
Both are in the capstone Deployment.

---

## Probes: is this pod ready? is it alive?

Two probes, two different questions ([`manifests/20-deployment.yaml`](../99_project_linkstash_k8s/manifests/20-deployment.yaml)):

```yaml
          readinessProbe:            # "should this pod receive traffic yet?"
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 2
            periodSeconds: 5
          livenessProbe:             # "is this pod still healthy, or should I restart it?"
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 5
            periodSeconds: 10
```

| Probe | Fails → | Purpose |
|---|---|---|
| **readiness** | pod removed from the Service's endpoints (no traffic) | don't send requests to a pod that's still starting or overloaded |
| **liveness** | pod is **restarted** | recover a hung/deadlocked process |
| **startup** (optional) | holds off the others until the app has booted | slow-starting apps |

This is why the linkstash app has a `/health` endpoint — it's not decoration, it's
the contract Kubernetes uses to route traffic and decide restarts. During the
verified rolling restart, a new pod received traffic **only after** its readiness
probe passed, which is what makes the restart zero-downtime.

> **readiness vs liveness matters:** a too-aggressive *liveness* probe restart-loops
> a pod that's just slow; a missing *readiness* probe sends traffic to a
> not-yet-ready pod (users get errors during deploys). Get readiness right first.

---

## Resources: requests & limits

```yaml
          resources:
            requests:               # what the scheduler reserves (guaranteed)
              cpu: "50m"            # 50 millicores = 0.05 CPU
              memory: "64Mi"
            limits:                 # the hard cap (throttled/killed if exceeded)
              cpu: "250m"
              memory: "128Mi"
```

- **requests** — the scheduler uses these to place the pod on a node with room;
  they're the pod's *guaranteed* share.
- **limits** — the ceiling. Exceed the **memory** limit → the pod is **OOM-killed**
  and restarted; exceed the **CPU** limit → it's **throttled** (not killed).

Set both, and set them from real measurements. No requests → the scheduler can
overpack a node and everything degrades; no limits → one buggy pod starves its
neighbours. This is the difference between a cluster that stays healthy under load
and one that cascades.

---

## Recap & next

- ✅ **readinessProbe** gates traffic (removed from Service on failure);
  **livenessProbe** restarts a hung pod. `/health` is the contract for both.
- ✅ **requests** = guaranteed/scheduled share; **limits** = hard cap (memory over →
  OOM-kill; CPU over → throttle). Set both.
- ✅ Probes + resources are what make rollouts zero-downtime and clusters stable
  under load.

## Exercise

Your app takes 30 s to warm up a model on boot. With only a `livenessProbe`
(`initialDelaySeconds: 5`), what goes wrong, and which probe(s) fix it?

<details>
<summary>Answer</summary>

The liveness probe starts checking at 5 s, fails while the model is still loading,
and Kubernetes **restarts the pod** — forever (a restart loop; it never gets to
finish warming up). Fix with a **startupProbe** (or a generous `initialDelaySeconds`)
to give it time to boot, plus a **readinessProbe** so it receives no traffic until
warm. Liveness should only catch *hangs after* startup.

</details>

**→ Next: [02-3 · Scaling & rollouts](03_scaling_and_rollouts.md)**
