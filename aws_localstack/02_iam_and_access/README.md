# 02 · IAM & access

Every AWS call is an authorization decision before it's anything else. A bucket, a
table, a queue, a function — each one is gated by **IAM**, so this section comes
*before* the services: you can't reason about S3 without knowing who's allowed to
call it. You'll learn the model, then the concrete roles and least-privilege
policies each service actually needs.

| # | Module | Services | You'll be able to… |
|---|---|---|---|
| 02-1 | [Identity: IAM & STS](01_access_model_iam_sts.md) | IAM, STS | Model principals, roles, and policies — and know Floci's IAM caveat |
| 02-2 | [IAM in practice](02_roles_and_policies_per_service.md) | IAM (per service) | Write the real trust + least-privilege policies each service needs |

> ⚠️ **Read the caveat in 02-1.** Floci **creates** IAM objects but
> **doesn't enforce** them — every call passes regardless of policy. You author and
> verify *policy documents* here; verify actual allow/deny on real AWS. This
> create-vs-enforce split recurs throughout the course (security groups in
> [section 07](../07_networking_and_compute/README.md), KMS in
> [06-3](../06_more_services/03_kms.md)).

**Next → [02-1 · Identity: IAM & STS](01_access_model_iam_sts.md)**
