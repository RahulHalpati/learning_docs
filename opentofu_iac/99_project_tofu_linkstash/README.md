# 99 · Capstone — provision linkstash with OpenTofu

Declarative infrastructure that stands up the `linkstash` app from the
[CI/CD course](../../cicd_github_actions/) — a Docker image, network, and container
— reproducibly, with `tofu apply`, and tears it down with `tofu destroy`. Runs
entirely against your local Docker daemon; no cloud account.

```
tofu apply → docker_network + docker_image + docker_container → app serving on :8088
tofu destroy → all gone
```

---

## Layout

```
99_project_tofu_linkstash/
├── versions.tf        # OpenTofu + docker provider requirements; provider config
├── main.tf            # calls the webservice module for linkstash
├── variables.tf       # image, environment, external_port (with validation)
├── outputs.tf         # url, container_name
├── Makefile           # image / init / plan / apply / verify / destroy
└── modules/
    └── webservice/    # reusable: run one containerised web service
        ├── versions.tf   # required_providers with SOURCE (the gotcha)
        ├── main.tf       # docker_network + docker_image + docker_container
        ├── variables.tf  # name, image, ports, env, keep_image_locally
        └── outputs.tf    # container_name, url, network
```

---

## Quick start

```bash
# 1. build the image the config references (from the CI/CD course capstone)
make image        # docker build --load -t linkstash:local ../../../cicd_github_actions/99_project_cicd_pipeline

# 2. the OpenTofu workflow
make init         # tofu init  — download the docker provider
make plan         # tofu plan  — preview (3 to add)
make apply        # tofu apply — create network + image + container
make verify       # curl $(tofu output -raw url)/health
make destroy      # tofu destroy — remove everything
```

### Verified output (2026-07-16, OpenTofu v1.12.4, Docker 29.6.1)

```
$ tofu init
OpenTofu has been successfully initialized!

$ tofu validate
Success! The configuration is valid.

$ tofu plan
Plan: 3 to add, 0 to change, 0 to destroy.

$ tofu apply
Apply complete! Resources: 3 added, 0 changed, 0 destroyed.
Outputs:
url = "http://127.0.0.1:8088"

$ curl http://127.0.0.1:8088/health
{"status":"ok","version":"1.2.0"}

$ tofu plan          # idempotent
No changes. Your infrastructure matches the configuration.

$ tofu destroy
Destroy complete! Resources: 3 destroyed.
```

---

## What it demonstrates

| Concept | Where |
|---|---|
| Provider + version constraints | `versions.tf` (`kreuzwerker/docker ~> 3.0`) |
| Resources & implicit dependencies | `modules/webservice/main.tf` (container refs image + network) |
| Variables with **validation** | `variables.tf` (`environment`, `external_port`) |
| **Module** with inputs/outputs | `modules/webservice/` |
| Outputs feeding a smoke test | `outputs.tf` + `make verify` |
| The **module-provider-source** gotcha | `modules/webservice/versions.tf` |

---

## Two real bugs this capstone caught (and teaches)

1. **Module provider source** — without `required_providers` *in the module*,
   `init` failed: *requires provider hashicorp/docker … isn't available*. Fix:
   declare `source = "kreuzwerker/docker"` in the module ([03-1](../03_modularizing/01_modules.md)).
2. **Local image not loaded** — `apply` tried to *pull* `linkstash:local` because
   buildx hadn't loaded it into the image store. Fix: `docker build --load`
   ([02-4](../02_core_workflow/04_provisioning_linkstash.md)).

---

## Going to the cloud

Swap the Docker provider for `aws`/`google`/`azurerm` and the resources change
(`aws_ecs_service`, `google_cloud_run_service`, …) — but `init/plan/apply`,
variables, modules, state, and the CI integration ([04-2](../04_production/02_cicd_integration.md))
are identical. That's the payoff of learning the workflow on a free, local provider.

→ Course starts at the **[README](../README.md)** → **[00 · Introduction](../00_introduction.md)**.
