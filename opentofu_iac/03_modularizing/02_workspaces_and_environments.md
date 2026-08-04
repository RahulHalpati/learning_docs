# 03-2 · Workspaces & environments

> **Level:** Intermediate · **Prerequisites:** [03-1 Modules](01_modules.md)
> **Time:** 20 min · **Verified:** 2026-07-16

You need staging *and* production from the same code, each with its own state so
they never clobber each other. Two patterns do this — workspaces and per-env
directories. Know when to use which.

---

## Pattern A: workspaces

A **workspace** is a named, separate state within one config. Same `.tf`, different
state per workspace:

```bash
tofu workspace new staging
tofu workspace new production
tofu workspace select staging
tofu apply -var="environment=staging"      # writes to the "staging" state
tofu workspace select production
tofu apply -var="environment=production" -var="external_port=8090"
```

Reference the current workspace in config:

```hcl
name = "linkstash-${terraform.workspace}"    # linkstash-staging / linkstash-production
```

The capstone is workspace-ready: its `environment` variable and name interpolation
mean `tofu workspace select production` + the right vars gives you an isolated prod
instance with its own state.

- 👍 Lightweight — one config, one place.
- 👎 Environments share the **same backend and code**, so it's easy to apply to the
  wrong one; big differences between envs get awkward.

---

## Pattern B: directory per environment

Separate directories, each with its own backend/state, sharing modules:

```
environments/
├── staging/     main.tf → module "app" { source = "../../modules/webservice" ... }
└── production/  main.tf → module "app" { source = "../../modules/webservice" ... }
modules/
└── webservice/
```

- 👍 Strong isolation — different backends, clear blast radius, per-env differences
  are natural.
- 👎 More files; shared changes go in the module (which is the point of
  [03-1](01_modules.md)).

---

## Which to use

| Situation | Prefer |
|---|---|
| Envs are near-identical, small team | **Workspaces** |
| Envs differ meaningfully, or need separate backends/permissions | **Directory per env** |
| Production isolation and blast-radius control matter | **Directory per env** |

Most teams outgrow workspaces into directory-per-env as production stakes rise —
the strong isolation is worth the extra files. Either way, **modules do the
sharing**; workspaces/dirs do the isolating.

---

## Recap & next

- ✅ Both patterns run one codebase for many environments with **separate state**
  per env.
- ✅ **Workspaces** = named states in one config (light, but shared backend/code);
  **directory-per-env** = stronger isolation (separate backends, more files).
- ✅ **Modules** provide the shared building blocks in both; pick isolation by how
  much prod isolation you need.

**Self-check:** Why must staging and production have *separate state*, whichever
pattern you choose?

<details>
<summary>Answer</summary>

State is the record of real resources ([01-4](../01_foundations/04_state.md)). If
staging and production shared one state, an apply meant for staging could plan
changes to production's resources (or vice versa), and a `destroy` could take down
the wrong environment. Separate state = separate, isolated blast radius.

</details>

**→ Next: [04-1 · Remote state & locking](../04_production/01_remote_state_and_locking.md)**
