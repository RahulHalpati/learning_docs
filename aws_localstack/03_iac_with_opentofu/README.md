# 03 · Infrastructure as Code

Stop creating resources by hand. Point the OpenTofu `aws` provider at LocalStack
and provision the whole `linkstash-cloud` stack declaratively — the same workflow
you'd use for real AWS.

| # | Module | You'll be able to… |
|---|---|---|
| 03-1 | [The aws provider against LocalStack](01_aws_provider_against_localstack.md) | Configure the real `aws` provider to target LocalStack |
| 03-2 | [The linkstash-cloud stack](02_the_capstone_stack.md) | Provision DynamoDB + S3 + SQS with one `tofu apply` |

> Uses the [OpenTofu course](../../opentofu_iac/) — do that first if `init/plan/apply`
> are new.

**Next → [03-1 · The aws provider against LocalStack](01_aws_provider_against_localstack.md)**
