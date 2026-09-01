# 05-3 · Gotchas, persistence & fidelity

> **Level:** Intermediate · **Prerequisites:** [05-2 Floci in CI](02_floci_in_ci.md)
> **Time:** 20 min · **Verified:** 2026-09-01

The operational realities — including the industry shake-up that explains why this
course runs Floci. Knowing these keeps an emulator a help, not a source of
confusing failures.

---

## The LocalStack sunset (why this course runs Floci)

**LocalStack** created this category, and for years its free Community edition was
the default answer. That ended on **March 23, 2026**: the images were unified
behind a required account + `LOCALSTACK_AUTH_TOKEN`, the open-source GitHub repo
(~65k stars) was archived, and the last token-free images (e.g. `3.8.1`) stopped
receiving updates and security patches. Building an earlier version of this course,
`localstack start` on CLI **2026.6.1** failed with exactly:

```
❌ Error: LocalStack requires an account to run.
==> Have an account? Learn how to set LOCALSTACK_AUTH_TOKEN ...
```

The community's answer was **Floci** — MIT-licensed, free forever, and deliberately
**drop-in compatible**: same `:4566`, same `/_localstack/health` path, LocalStack
env vars auto-translated (`PERSISTENCE=1` → `FLOCI_STORAGE_MODE=persistent`), and
`/etc/localstack/init/` scripts run unchanged. This whole course was re-verified
end to end against Floci (capstone: 6 resources, 7/7 tests).

If a job hands you a **licensed LocalStack**, everything here maps 1:1 — swap the
image and set the token ([05-2](02_floci_in_ci.md)). Knowing this story is
itself interview-useful: it shows you follow your tooling's supply chain.

---

## Ephemerality & persistence

By default **Floci forgets everything on restart** — great for tests (clean
slate), surprising if you expected data to survive:

```bash
docker rm -f floci && docker run ... floci/floci:latest   # ← your S3/DynamoDB data is gone
```

- **Embrace it for tests** — provision with `tofu apply` at the start of each run.
- **Need data to survive a restart?** Opt in with `FLOCI_STORAGE_MODE=persistent`
  and a volume (`-v ./data:/app/data`). For tests, prefer the clean slate.

This is why the capstone re-runs `make apply` + `make seed` rather than relying on
saved state.

---

## Emulation fidelity — where it differs from real AWS

An emulator is faithful but not identical. The seams that matter:

- **IAM isn't enforced** — everything is allowed, so the emulator won't catch a
  missing permission that real AWS would reject. (Floci has opt-in auth checking
  for S3 only, `FLOCI_SERVICES_S3_ENFORCE_AUTH`.) Test IAM policies on real AWS.
- **Stub services** — all ~100 services answer, but a few only return canned
  responses (Bedrock Runtime/AgentCore, Textract, Transcribe): fine for wiring
  tests, useless for behaviour.
- **Edge behaviour** — quotas, throttling, eventual-consistency timing, and some
  error shapes may differ.
- **Endpoints/URLs** — path-style S3, plain `http://localhost:4566/...` SQS URLs —
  cosmetic differences from real AWS you saw in the capstone output.

**So:** develop and integration-test on the emulator; do a final validation against
real AWS before production, especially for IAM and less-common services.

---

## When would you still pay for LocalStack?

Floci covers this course and most app dev for free — including services that used
to be paywalled (RDS/ElastiCache/MSK run as *real* Postgres/Redis/Kafka engines,
Lambda executes in real Docker). A **licensed LocalStack** still earns its price
for: full **IAM enforcement**, **cloud pods** (shareable state snapshots), the web
UI, deeper emulation of niche services, and enterprise support. Decide per
project; the code you write is identical either way.

---

## Recap & next

- ✅ **LocalStack sunset its free edition in March 2026** — Floci is the free,
  drop-in, maintained replacement this course uses.
- ✅ State is **ephemeral** by default (persistence: `FLOCI_STORAGE_MODE=persistent`)
  — re-`apply`/seed per run; perfect for tests.'),
- ✅ **Fidelity gaps** (no IAM enforcement, partial coverage, edge behaviour) →
  validate on real AWS before production.

**Self-check:** Your app works flawlessly on the emulator but gets `AccessDenied` the
moment it hits real AWS. What's the most likely cause, given this module?

<details>
<summary>Answer</summary>

**Missing/incorrect IAM permissions.** The emulator doesn't enforce IAM, so
it never rejected the call — real AWS does. This is the classic fidelity gap: always
test IAM policies against real AWS, because a
green emulator run can't validate permissions.

</details>

**→ Next: [06 · More AWS services](../06_more_services/README.md)** — config &
secrets, events & orchestration, and identity. Or jump to the
**[99 · Capstone: linkstash-cloud](../99_project_linkstash_cloud/README.md)**.
