# 04 · Security & RBAC

Snowflake's access control looks familiar and behaves differently: privileges are
never attached to a person, they are granted to **roles**, and roles are granted to
users or to other roles. Get the shape right once — access roles under functional
roles, **future grants** so tomorrow's tables inherit today's decisions — and
**least privilege** stops being a chore you re-do every migration.

| # | Module | You'll be able to… |
|---|---|---|
| 04-1 | [The RBAC model](01_rbac_model.md) | Reason in privileges→roles→users, name the four grants a `SELECT` needs, and map the whole model onto the IAM you already know |
| 04-2 | [Roles & grants in practice](02_roles_and_grants_in_practice.md) | Build the linkstash role hierarchy in SQL, cover new tables with future grants, and prove a denial actually happens |
| 04-3 | [Governance: masking, row access & network policies](03_data_governance.md) | Mask PII per role, restrict rows and IPs, and audit who read what — knowing which of it is Enterprise-only |

> Unlike the LocalStack half of your AWS course, **this is really enforced.** There
> is no "creates but doesn't check" caveat here — a missing grant produces a real
> error on a real account, which means for the first time you can *test* your
> access model instead of merely authoring it.

**Next → [04-1 · The RBAC model](01_rbac_model.md)**
