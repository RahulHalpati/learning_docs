# 04-3 · Gotchas, persistence & Pro

> **Level:** Intermediate · **Prerequisites:** [04-2 LocalStack in CI](02_localstack_in_ci.md)
> **Time:** 20 min · **Verified:** 2026-07-16

The operational realities — including the one that bit this very course. Knowing
these keeps LocalStack a help, not a source of confusing failures.

---

## The account-requirement gotcha (real, hit here)

LocalStack's **2026 releases require a free account** and a `LOCALSTACK_AUTH_TOKEN`
even for community use. Building this course, `localstack start` on CLI **2026.6.1**
failed with:

```
❌ Error: LocalStack requires an account to run.
==> Have an account? Learn how to set LOCALSTACK_AUTH_TOKEN ...
```

Two ways through it:

1. **Pin a token-free image** (what this course does):
   ```bash
   docker run -d -p 4566:4566 localstack/localstack:3.8.1
   ```
   `3.8.1` (Oct 2024) runs community with **no signup** — reproducible and
   dependency-free, ideal for a course and for CI.
2. **Create a free account** at app.localstack.cloud, get a token, and set
   `LOCALSTACK_AUTH_TOKEN` — required for the latest image and its newest features.

Neither is wrong; pin for reproducibility, token for the newest features.

---

## Ephemerality & persistence

By default **LocalStack forgets everything on restart** — great for tests (clean
slate), surprising if you expected data to survive:

```bash
docker rm -f localstack_main && docker run ... localstack:3.8.1   # ← your S3/DynamoDB data is gone
```

- **Embrace it for tests** — provision with `tofu apply` at the start of each run.
- **Need data to survive a restart?** Persistence (saving/reloading state) is a
  **Pro** feature; in Community, re-`apply` your IaC and re-seed instead.

This is why the capstone re-runs `make apply` + `make seed` rather than relying on
saved state.

---

## Emulation fidelity — where it differs from real AWS

LocalStack is faithful but not identical. The seams that matter:

- **IAM isn't enforced** in Community — everything is allowed, so LocalStack won't
  catch a missing permission that real AWS would reject. Test IAM policies on real
  AWS.
- **Service coverage** — Community has the core; many services (RDS, ECS, …) are Pro
  or unavailable.
- **Edge behaviour** — quotas, throttling, eventual-consistency timing, and some
  error shapes may differ.
- **Endpoints/URLs** — path-style S3, the `*.localhost.localstack.cloud` SQS URLs —
  cosmetic differences you saw in the capstone output.

**So:** develop and integration-test on LocalStack; do a final validation against
real AWS before production, especially for IAM and less-common services.

---

## Community vs Pro — when to pay

| Need | Community (free) | Pro |
|---|---|---|
| S3, DynamoDB, SQS/SNS, Lambda, API GW, core | ✅ | ✅ |
| RDS, ECS, EKS, Cognito, AppSync, … | ✗ | ✅ |
| Persistence, cloud pods, IAM enforcement, web UI | ✗ | ✅ |

Most learning and a lot of app dev fit Community. Reach for Pro when you need a
service it doesn't have, want state persistence, or need IAM-accurate testing.

---

## Recap & next

- ✅ **2026 LocalStack needs a free account/token** — pin **`3.8.1`** to avoid it,
  or set `LOCALSTACK_AUTH_TOKEN`.
- ✅ State is **ephemeral** (persistence is Pro) — re-`apply`/seed per run; perfect
  for tests.
- ✅ **Fidelity gaps** (no IAM enforcement, partial coverage, edge behaviour) →
  validate on real AWS before production.

**Self-check:** Your app works flawlessly on LocalStack but gets `AccessDenied` the
moment it hits real AWS. What's the most likely cause, given this module?

<details>
<summary>Answer</summary>

**Missing/incorrect IAM permissions.** LocalStack Community doesn't enforce IAM, so
it never rejected the call — real AWS does. This is the classic fidelity gap: always
test IAM policies against real AWS (or LocalStack Pro's IAM enforcement), because a
green LocalStack run can't validate permissions.

</details>

**→ Next: [05 · More AWS services](../05_more_services/README.md)** — config &
secrets, events & orchestration, and identity. Or jump to the
**[99 · Capstone: linkstash-cloud](../99_project_linkstash_cloud/README.md)**.
