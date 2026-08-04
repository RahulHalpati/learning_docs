# 03-1 · The aws provider against LocalStack

> **Level:** Intermediate · **Prerequisites:** [02-2 DynamoDB](../02_core_services/02_dynamodb.md), [OpenTofu course](../../opentofu_iac/)
> **Time:** 25 min · **Verified:** 2026-07-16 (OpenTofu v1.12.4 + LocalStack 3.8.1)

Creating resources with `awslocal` by hand doesn't scale or reproduce. The
[OpenTofu course](../../opentofu_iac/) used the Docker provider; here you use the
**real `hashicorp/aws` provider** — just aimed at LocalStack. Your config becomes
production-ready by deleting a few lines.

---

## Point the aws provider at LocalStack

The capstone's [`infra/main.tf`](../99_project_linkstash_cloud/infra/main.tf):

```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"       # ignored by LocalStack
  secret_key                  = "test"
  s3_use_path_style           = true         # LocalStack S3 quirk (02-1)
  skip_credentials_validation = true         # no real STS to validate against
  skip_metadata_api_check     = true         # no EC2 metadata endpoint
  skip_requesting_account_id  = true         # no real account
  endpoints {
    dynamodb = "http://localhost:4566"
    s3       = "http://localhost:4566"
    sqs      = "http://localhost:4566"
  }
}
```

The `skip_*` flags exist because LocalStack has no real IAM/account/metadata to
answer those startup checks. The `endpoints` block redirects each service to
`:4566`.

---

## The magic: it's the same config as real AWS

The resources below are **ordinary AWS resources** — nothing LocalStack-specific:

```hcl
resource "aws_dynamodb_table" "links" {
  name         = "links"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "slug"
  attribute { name = "slug"  type = "S" }
}
resource "aws_s3_bucket" "backups" { bucket = "linkstash-backups" }
resource "aws_sqs_queue"  "events" { name   = "linkstash-events" }
```

**Delete the `endpoints`/`skip_*`/`access_key` lines and this provisions real
AWS.** That's the payoff: you develop and test the *exact* Terraform you'll ship,
against a free local target.

---

## Apply it — verified

```bash
cd infra && tofu init && tofu apply
```

Real output:

```
aws_s3_bucket.backups:    Creation complete after 1s  [id=linkstash-backups]
aws_dynamodb_table.links: Creation complete after 3s  [id=links]
aws_sqs_queue.events:     Creation complete after 26s [id=...linkstash-events]
Apply complete! Resources: 3 added, 0 changed, 0 destroyed.

Outputs:
bucket_name = "linkstash-backups"
queue_url   = "http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/linkstash-events"
table_name  = "links"
```

Three real AWS resource types, created on LocalStack, in one command.

---

## `tflocal` — the shortcut

LocalStack ships **`tflocal`**, a wrapper that injects the endpoints/skip config for
you, so your `.tf` can be endpoint-free:

```bash
pip install terraform-local
tflocal init && tflocal apply     # same as tofu, but auto-points at LocalStack
```

Handy, but writing the provider block once (as the capstone does) makes the
mechanism visible and keeps the config a single source of truth for local *and*
real AWS. Use whichever you prefer.

---

## Recap & next

- ✅ Use the **real `hashicorp/aws` provider** with an `endpoints` block + `skip_*`
  flags to target LocalStack.
- ✅ The resources are **ordinary AWS resources** — remove the LocalStack lines and
  the same config provisions real AWS.
- ✅ Verified: `tofu apply` created a DynamoDB table + S3 bucket + SQS queue;
  **`tflocal`** automates the endpoint wiring.

**Self-check:** Why does the provider need `skip_credentials_validation = true` and
friends for LocalStack, when a real-AWS provider doesn't set them?

<details>
<summary>Answer</summary>

On startup the aws provider normally validates credentials (via STS), checks the
EC2 metadata endpoint, and looks up the account id. LocalStack has no real
STS/metadata/account to answer those, so without the `skip_*` flags the provider
errors before it does anything. They tell it to skip those real-AWS handshakes.

</details>

**→ Next: [03-2 · The linkstash-cloud stack](02_the_capstone_stack.md)**
