# 04-3 · Best practices & gotchas

> **Level:** Intermediate · **Prerequisites:** [04-2 OpenTofu in CI/CD](02_cicd_integration.md)
> **Time:** 20 min · **Verified:** 2026-07-16

The practices that keep IaC safe, and the traps that bite everyone once. Several of
these are bugs actually hit while building this course.

---

## Do

- **Always read the plan.** Especially the `add/change/destroy` summary and any
  `-/+` (replace). This is the single most protective habit.
- **Pin versions.** `required_version` for OpenTofu and `~>` constraints for
  providers, plus commit the **`.terraform.lock.hcl`** lock file so everyone
  resolves identical provider versions.
- **Remote state + locking** for anything shared ([04-1](01_remote_state_and_locking.md)).
- **`fmt` + `validate` in CI**, and a **security scan** — `tfsec` or `checkov`
  catch insecure infra (a public S3 bucket, an open security group) the same way
  the [Secure Code Audit](../../secure_code_audit/) course scans app code.
- **Small, reviewed changes.** A focused plan is a readable plan.

## Don't

- **Don't edit state by hand.** Use `tofu state mv/rm/import` and `tofu import`.
- **Don't commit state or secrets.** `terraform.tfstate` and `*.tfvars` with
  secrets stay out of git ([`.gitignore`](../99_project_tofu_linkstash/.gitignore)).
  State holds secrets in plaintext.
- **Don't `apply` from a laptop against shared prod** once you have a pipeline — let
  CI hold the credentials and the lock.
- **Don't ignore drift.** If someone hotfixes in the console, reconcile it
  (`plan` → `apply` or update config) rather than letting code and reality diverge.

---

## Gotchas (learned the hard way here)

| Gotcha | Symptom | Fix |
|---|---|---|
| **Module provider source** | `init`: *requires provider hashicorp/docker, but that provider isn't available* | child module needs its own `required_providers` with `source` ([03-1](../03_modularizing/01_modules.md)) |
| **Local image not loaded** | `apply`: *unable to pull image linkstash:local … repository does not exist* | `docker build --load`; `docker_image` needs it present locally ([02-4](../02_core_workflow/04_provisioning_linkstash.md)) |
| **Unexpected replacement** | plan shows `-/+` on a stateful resource | check which attribute forces replacement; use `create_before_destroy` or migrate |
| **Lost/committed state** | duplicates or orphans | remote backend; never commit or delete state ([01-4](../01_foundations/04_state.md)) |
| **Drift** | plan shows changes you didn't make | reconcile; consider `ignore_changes` for legitimately-external attributes |

The first two are real errors this course hit and fixed — both surfaced by *reading
the error and the plan*, which is the meta-lesson.

---

## Importing existing infrastructure

Inherited a manually-created resource? Bring it under management with `import`
instead of recreating it:

```bash
tofu import docker_container.app <container-id>
```

Write the matching `resource` block, import the real object into state, then `plan`
until it shows **no changes** — now OpenTofu manages it safely.

---

## Recap & next

- ✅ **Do:** read the plan, pin versions + commit the lock file, remote state +
  locking, `fmt`/`validate`/security-scan in CI, small changes.
- ✅ **Don't:** hand-edit or commit state, keep secrets in git, apply to shared prod
  from a laptop, ignore drift.
- ✅ Know the **gotchas** (module provider source, local image, replacement, state,
  drift) and use **`import`** to adopt existing resources.

**Self-check:** You inherit infrastructure someone built by clicking in a console.
What's the safe way to bring it under OpenTofu without downtime?

<details>
<summary>Answer</summary>

**Import**, don't recreate. Write a `resource` block matching the real object,
`tofu import <address> <id>` to record it in state, then run `plan` and adjust your
config until it reports **no changes**. Now it's managed with zero disruption —
recreating instead would destroy and rebuild live infrastructure.

</details>

**Course complete.** → See it all assembled in the
**[99 · Capstone: provision linkstash](../99_project_tofu_linkstash/README.md)**.
You've now built the full path: **audit code → integrate & deploy (CI/CD) →
provision infrastructure (OpenTofu)**.
