# 03-1 · Modules

> **Level:** Intermediate · **Prerequisites:** [02-4 Provisioning linkstash](../02_core_workflow/04_provisioning_linkstash.md)
> **Time:** 25 min · **Verified:** 2026-07-16

A **module** is a reusable package of resources with inputs (variables) and outputs
— the function of infrastructure code. The capstone already uses one; here's how it
works and why.

---

## Any directory of `.tf` is a module

The root config is the **root module**. A directory it calls is a **child module**.
The capstone's [`modules/webservice/`](../99_project_tofu_linkstash/modules/webservice/)
is a child module that packages "one containerised web service":

```
99_project_tofu_linkstash/
├── main.tf            # root module — calls the child
├── variables.tf
├── outputs.tf
└── modules/
    └── webservice/    # child module
        ├── main.tf      # docker_network + docker_image + docker_container
        ├── variables.tf # name, image, ports, env  (its INPUTS)
        ├── outputs.tf   # url, container_name       (its OUTPUTS)
        └── versions.tf  # required_providers (source!)
```

---

## Calling a module

A `module` block passes inputs and gets a reusable unit — from the root
[`main.tf`](../99_project_tofu_linkstash/main.tf):

```hcl
module "linkstash" {
  source        = "./modules/webservice"    # local path (or a registry/git URL)
  name          = "linkstash-${var.environment}"
  image         = var.image
  external_port = var.external_port
  env           = { HOST = "0.0.0.0", PORT = "8000" }
}
```

Read the module's outputs with `module.NAME.OUTPUT`:

```hcl
output "url" { value = module.linkstash.url }
```

`source` can be a local path (`./modules/...`), a **Git URL**, or the **OpenTofu
Registry** — so modules are shareable across projects and teams.

---

## Why modules

- **Reuse** — provision three services by calling the module three times with
  different inputs, instead of copy-pasting three sets of resources.
- **Encapsulation** — callers pass `name`/`image`/`port` and don't care that inside
  there's a network + image + container.
- **Consistency** — every service provisioned through the module gets the same
  healthcheck, restart policy, and network setup.

```hcl
module "linkstash" { source = "./modules/webservice"  name = "linkstash"  image = "linkstash:local"  external_port = 8088 }
module "analytics" { source = "./modules/webservice"  name = "analytics"  image = "analytics:local"  external_port = 8089 }
```

Two services, one module, zero duplication.

---

## The provider gotcha (again)

A child module that uses a provider whose source isn't `hashicorp/*` **must declare
that source itself**, in its own `required_providers`. The capstone's
[`modules/webservice/versions.tf`](../99_project_tofu_linkstash/modules/webservice/versions.tf):

```hcl
terraform {
  required_providers {
    docker = { source = "kreuzwerker/docker", version = "~> 3.0" }
  }
}
```

Without this, `init` failed with *"requires provider hashicorp/docker, but that
provider isn't available"* — a real error hit while building this course. The
module names the *source*; the root still *configures* the provider. This is the
#1 module gotcha.

---

## Recap & next

- ✅ A **module** is a directory of `.tf` with **inputs (variables)** and
  **outputs**; the root calls children via `module "..." { source = ... }`.
- ✅ Modules give **reuse, encapsulation, consistency**; `source` can be local, Git,
  or the registry.
- ✅ A child module must **declare the `source` of non-hashicorp providers** in its
  own `required_providers`, or `init` fails.

**Self-check:** You copy the `webservice` module's resources directly into your root
`main.tf` instead of calling it as a module. It works. What did you lose?

<details>
<summary>Answer</summary>

**Reuse and encapsulation.** Inlined, provisioning a second service means copy-
pasting and maintaining two divergent copies. As a module, a second service is one
more `module` block with different inputs, and a fix to the module benefits every
caller. You also lose the clean input/output contract that documents what the unit
needs.

</details>

**→ Next: [03-2 · Workspaces & environments](02_workspaces_and_environments.md)**
