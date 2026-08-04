# 01-3 · The HCL language

> **Level:** Beginner · **Prerequisites:** [01-2 Install & first apply](02_install_and_first_apply.md)
> **Time:** 25 min · **Verified:** 2026-07-16

OpenTofu configs are written in **HCL** (HashiCorp Configuration Language) — a
small, readable language built around **blocks**. Learn the handful of block types
and you can read any `.tf` file.

---

## Everything is a block

A block is `TYPE "LABEL"... { arguments }`:

```hcl
resource "docker_container" "app" {   # type=resource, labels=[docker_container, app]
  name  = "linkstash"                 # an argument (string)
  image = docker_image.app.image_id   # an argument (a reference)
}
```

The block types you'll use:

| Block | Purpose |
|---|---|
| `terraform { }` | version + provider requirements ([`versions.tf`](../99_project_tofu_linkstash/versions.tf)) |
| `provider "docker" { }` | configure a provider |
| `resource "TYPE" "NAME" { }` | **a thing to create** (the core) |
| `variable "NAME" { }` | an input ([02-2](../02_core_workflow/02_variables_and_outputs.md)) |
| `output "NAME" { }` | a value to expose |
| `module "NAME" { }` | reuse a group of resources ([03-1](../03_modularizing/01_modules.md)) |
| `data "TYPE" "NAME" { }` | read something that already exists |

---

## Resources and references

A **resource** declares one managed object. Its address is `TYPE.NAME`
(`docker_container.app`), and you read its attributes with dots:

```hcl
resource "docker_image" "app" {
  name = "linkstash:local"
}

resource "docker_container" "app" {
  image = docker_image.app.image_id   # ← reference creates a dependency (02-3)
}
```

That reference does two things: it plugs the image's id into the container, **and**
tells OpenTofu the image must be created first. You almost never write explicit
ordering — references imply it.

---

## Types & expressions

HCL has the types you'd expect and interpolation with `${}`:

```hcl
variable "environment" { type = string }
variable "port"        { type = number }
variable "enabled"     { type = bool }
variable "env"         { type = map(string) }   # {"HOST"="0.0.0.0"}
variable "zones"       { type = list(string) }  # ["a","b"]

name = "linkstash-${var.environment}"           # interpolation
```

Useful expression features you'll meet in the capstone:

```hcl
# a for-expression: turn a map into Docker's ["KEY=value", ...] form
env = [for k, v in var.env : "${k}=${v}"]

# a conditional
restart = var.environment == "production" ? "always" : "unless-stopped"

# a validation rule on an input
validation {
  condition     = var.port > 1024 && var.port < 65536
  error_message = "port must be unprivileged."
}
```

(The `for` expression and `validation` block are both taken from the capstone's
[`modules/webservice`](../99_project_tofu_linkstash/modules/webservice/).)

---

## fmt & validate

Two commands keep your HCL clean — and they're free CI checks ([04-2](../04_production/02_cicd_integration.md)):

```bash
tofu fmt -recursive   # canonical formatting (like ruff format / gofmt)
tofu validate         # syntax + internal consistency, no cloud calls
```

Verified on the capstone: `tofu validate` → `Success! The configuration is valid.`

---

## Recap & next

- ✅ HCL is **blocks**: `terraform`, `provider`, `resource`, `variable`, `output`,
  `module`, `data`.
- ✅ A **resource** (`TYPE.NAME`) declares one object; **references** between
  resources both pass values and imply ordering.
- ✅ HCL has real **types and expressions** (`for`, conditionals, `validation`);
  `tofu fmt` + `validate` keep configs clean.

**Self-check:** In `image = docker_image.app.image_id`, what two things does that
reference accomplish?

<details>
<summary>Answer</summary>

(1) It **passes the value** — the created image's id becomes the container's image.
(2) It **creates a dependency** — OpenTofu knows `docker_image.app` must be created
before `docker_container.app`, so you don't need an explicit `depends_on`.

</details>

**→ Next: [01-4 · State](04_state.md)**
