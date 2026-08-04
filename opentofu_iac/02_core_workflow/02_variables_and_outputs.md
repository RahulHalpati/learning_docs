# 02-2 · Variables & outputs

> **Level:** Beginner · **Prerequisites:** [02-1 Providers & resources](01_providers_and_resources.md)
> **Time:** 20 min · **Verified:** 2026-07-16

Hardcoded configs aren't reusable. **Variables** are the inputs; **outputs** are the
results you expose. Together they turn a one-off config into something you can run
for staging *and* production.

---

## Variables: typed, defaulted, validated

A `variable` block declares an input. From the capstone's
[`variables.tf`](../99_project_tofu_linkstash/variables.tf):

```hcl
variable "environment" {
  type        = string
  default     = "staging"
  description = "Logical environment name; used in resource names."

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

variable "external_port" {
  type    = number
  default = 8088
}
```

Read them with `var.NAME`:

```hcl
name          = "linkstash-${var.environment}"
external_port = var.external_port
```

- **`type`** catches mistakes early (`number` rejects `"eight"`).
- **`default`** makes a variable optional; omit it to force the caller to supply one.
- **`validation`** rejects bad values with a helpful message *before* apply — the
  capstone validates the port is unprivileged and the environment is known.

---

## Setting variable values

Several ways, in increasing precedence:

| Method | Example |
|---|---|
| `default` in the block | `default = "staging"` |
| `terraform.tfvars` / `*.auto.tfvars` | `environment = "production"` |
| `-var` flag | `tofu apply -var="environment=production"` |
| `-var-file` | `tofu apply -var-file=prod.tfvars` |
| `TF_VAR_` env var | `TF_VAR_environment=production tofu apply` |

A `terraform.tfvars` file is the usual home for a given environment's values; the
CLI flags override it for one-off runs.

> **Secrets:** don't put secrets in `.tfvars` committed to git. Use
> `TF_VAR_*` env vars (from your secret store / CI) or a secrets manager — same
> rule as state ([01-4](../01_foundations/04_state.md)).

---

## Outputs: expose the results

An `output` surfaces a value after apply — for humans, or for other tooling. From
the capstone's [`outputs.tf`](../99_project_tofu_linkstash/outputs.tf):

```hcl
output "url" {
  value       = module.linkstash.url
  description = "Where linkstash is serving."
}
```

Verified after apply:

```
$ tofu output
container_name = "linkstash-staging"
url            = "http://127.0.0.1:8088"
```

Get one value for scripting with `tofu output -raw url` — which is exactly how the
capstone's `make verify` target smoke-tests the running service:

```make
verify:
	curl -fsS $$(tofu output -raw url)/health && echo " OK"
```

---

## Recap & next

- ✅ **Variables** are typed, optionally defaulted, and can **validate** inputs
  before apply; read with `var.NAME`.
- ✅ Set them via `default`, `.tfvars`, `-var`, or `TF_VAR_*` (increasing
  precedence); keep **secrets out of committed tfvars**.
- ✅ **Outputs** expose results (`tofu output`, `-raw` for scripts) — the capstone
  feeds `url` into its smoke test.

**Self-check:** You want the same config to run for staging and production with
different ports. What do you change between runs — the `.tf` files or something
else?

<details>
<summary>Answer</summary>

Not the `.tf` files — you change the **variable values**: a `-var`/`-var-file`, a
per-env `.tfvars`, or `TF_VAR_*`. The config stays identical; only inputs differ.
That's the whole point of variables (and, at a larger scale, workspaces/modules —
[03](../03_modularizing/)).

</details>

**→ Next: [02-3 · Dependencies & lifecycle](03_dependencies_and_lifecycle.md)**
