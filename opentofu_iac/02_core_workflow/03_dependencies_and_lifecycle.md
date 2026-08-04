# 02-3 · Dependencies & lifecycle

> **Level:** Intermediate · **Prerequisites:** [02-2 Variables & outputs](02_variables_and_outputs.md)
> **Time:** 20 min · **Verified:** 2026-07-16

OpenTofu figures out *what order* to create things, and *how* to change them when
your config changes. Understanding both saves you from mysterious plans.

---

## Implicit dependencies (the usual case)

When one resource **references** another, OpenTofu infers the order. In the
capstone:

```hcl
resource "docker_image" "this"     { name = var.image }
resource "docker_network" "this"   { name = "${var.name}-net" }
resource "docker_container" "this" {
  image = docker_image.this.image_id            # needs the image
  networks_advanced { name = docker_network.this.name }   # needs the network
}
```

The container references both the image and the network, so OpenTofu builds a
**dependency graph** and creates image + network first, container last — which is
exactly what the verified apply did:

```
docker_network.this: Creation complete
docker_image.this:   Creation complete
docker_container.this: Creation complete      # last
```

You wrote no ordering; the references *are* the ordering.

---

## Explicit dependencies (`depends_on`)

Occasionally there's a dependency with **no reference** between the resources (an
IAM policy that must exist before a service uses it, say). Force the order with
`depends_on`:

```hcl
resource "docker_container" "app" {
  # ...
  depends_on = [docker_network.this]   # wait even without a reference
}
```

Reach for it only when there's no natural reference — overusing it hides the graph
and slows applies.

---

## The lifecycle block

`lifecycle` controls *how* a resource is changed when the plan says it must:

```hcl
resource "docker_container" "app" {
  # ...
  lifecycle {
    create_before_destroy = true   # make the new one before killing the old → less downtime
    prevent_destroy       = true   # refuse to destroy this (guard a database)
    ignore_changes        = [env]  # don't fight external changes to these attributes
  }
}
```

| Setting | Use when |
|---|---|
| `create_before_destroy` | replacing a resource shouldn't cause a gap (blue-green-ish) |
| `prevent_destroy` | a resource must never be accidentally deleted (prod DB) |
| `ignore_changes` | something outside OpenTofu legitimately changes an attribute |

---

## Change vs. replace

When you edit a resource, the provider decides whether the change is:

- **In-place update** (`~` in the plan) — e.g. changing a container's `restart`
  policy, or
- **Replacement** (`-/+` in the plan) — destroy and recreate, because the attribute
  can't be changed live (e.g. a container's `image`).

**Read which one the plan shows.** A replacement of a stateful resource (database,
volume) can mean data loss — that's when `create_before_destroy` or a migration
plan matters. This is the deeper reason 01-2 said *always read the plan*.

---

## Recap & next

- ✅ **References imply order** — OpenTofu builds a dependency graph; you rarely
  order things manually.
- ✅ Use **`depends_on`** only for dependencies with no reference.
- ✅ **`lifecycle`** tunes replacement (`create_before_destroy`, `prevent_destroy`,
  `ignore_changes`); watch the plan for **in-place (`~`) vs replace (`-/+`)**.

**Self-check:** Your plan shows `docker_container.app must be replaced` after you
changed its `image`. Why replace instead of update, and what would reduce the
downtime?

<details>
<summary>Answer</summary>

A container's image can't be swapped on a running container, so the provider marks
the change as **replacement** (destroy + recreate). `lifecycle { create_before_destroy
= true }` builds the new container before removing the old, shrinking the gap — the
IaC echo of the blue-green idea from the CI/CD course.

</details>

**→ Next: [02-4 · Provisioning linkstash](04_provisioning_linkstash.md)**
