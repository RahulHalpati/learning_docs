# 04 · Infrastructure as Code

Stop creating resources by hand. Point the OpenTofu `aws` provider at Floci
and provision the whole `linkstash-cloud` stack declaratively — the same workflow
you'd use for real AWS.

| # | Module | You'll be able to… |
|---|---|---|
| 04-1 | [The aws provider against Floci](01_aws_provider_against_floci.md) | Configure the real `aws` provider to target Floci |
| 04-2 | [The linkstash-cloud stack](02_the_capstone_stack.md) | Provision DynamoDB + S3 + SQS with one `tofu apply` |

> Uses the [OpenTofu course](../../opentofu_iac/) — do that first if `init/plan/apply`
> are new.

**Next → [04-1 · The aws provider against Floci](01_aws_provider_against_floci.md)**
