# 02-1 · Providers & resources

> **Level:** Beginner · **Prerequisites:** [01-4 State](../01_foundations/04_state.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (kreuzwerker/docker ~> 3.0)

**Providers** are the plugins that let OpenTofu talk to a platform (AWS, GCP,
Kubernetes, Docker…). **Resources** are the things a provider can manage. Together
they're 90% of any config.

---

## Declaring a provider

You state which providers you need (and versions) in a `terraform` block, then
configure them. From the capstone's [`versions.tf`](../99_project_tofu_linkstash/versions.tf):

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"   # registry namespace/name
      version = "~> 3.0"               # allow 3.x, not 4.0
    }
  }
}

provider "docker" {}   # default config talks to the local Docker socket
```

`tofu init` reads this and downloads the provider. **Version constraints matter**:
`~> 3.0` means "≥3.0, <4.0" — you get patches/features but not a breaking major.

> **`source` is required for non-hashicorp providers.** `kreuzwerker/docker` isn't
> `hashicorp/docker` (which doesn't exist). Omitting `source` makes OpenTofu guess
> `hashicorp/docker` and fail — a gotcha you'll hit again with modules in
> [03-1](../03_modularizing/01_modules.md).

---

## Resources: the things you create

A `resource` block = one managed object. The capstone's
[`modules/webservice/main.tf`](../99_project_tofu_linkstash/modules/webservice/main.tf)
declares three:

```hcl
resource "docker_network" "this" {
  name = "${var.name}-net"
}

resource "docker_image" "this" {
  name         = var.image          # "linkstash:local"
  keep_locally = true               # use the local build; don't pull from a registry
}

resource "docker_container" "this" {
  name  = var.name
  image = docker_image.this.image_id       # ← reference → dependency + value

  networks_advanced { name = docker_network.this.name }
  ports { internal = 8000, external = var.external_port }
  env   = [for k, v in var.env : "${k}=${v}"]
  restart = "unless-stopped"
}
```

Each resource's **schema** (its valid arguments — `ports`, `env`, `restart`) comes
from the provider's docs. You look up the resource type (`docker_container`), see
its arguments, and fill them in.

---

## Data sources: read, don't create

Sometimes you need to *reference* something that already exists (an existing
network, an AMI, the current AWS account). That's a `data` block — read-only:

```hcl
data "docker_network" "existing" {
  name = "bridge"                 # look it up, don't manage it
}
# use it: data.docker_network.existing.id
```

Resource = "make this exist and manage it." Data source = "find this and read it."

---

## Recap & next

- ✅ **Providers** (plugins) are declared in `required_providers` with a `source`
  and `version`; `init` downloads them.
- ✅ **Resources** (`resource "TYPE" "NAME"`) are objects OpenTofu creates and
  manages; their arguments come from the provider schema.
- ✅ **Data sources** (`data`) *read* existing things without managing them.

**Self-check:** Why does `docker` need `source = "kreuzwerker/docker"` while
`aws` usually needs no explicit source?

<details>
<summary>Answer</summary>

Providers published by HashiCorp (like `aws` → `hashicorp/aws`) are the default
namespace, so OpenTofu finds them without an explicit `source`. The Docker provider
is community-maintained under `kreuzwerker/`, not `hashicorp/`, so you must state
its `source` — otherwise OpenTofu looks for the nonexistent `hashicorp/docker`.

</details>

**→ Next: [02-2 · Variables & outputs](02_variables_and_outputs.md)**
