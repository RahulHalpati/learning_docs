# 00 · Introduction

> **Level:** Beginner → Intermediate · **Time:** 15 min · **Verified:** 2026-07-16 (LocalStack 3.8.1)

Learning AWS usually means a credit card, a fear of surprise bills, and slow
network round-trips. **LocalStack removes all three**: it runs the AWS APIs in a
container on your machine, so you learn and build against S3, DynamoDB, SQS, and
Lambda for free, offline, and instantly.

---

## What you'll build

The `linkstash` app you met in the [CI/CD](../cicd_github_actions/) and
[OpenTofu](../opentofu_iac/) courses — now **cloud-native**. Its data moves into
AWS services, provisioned with OpenTofu and exercised with the AWS SDK, all on
LocalStack:

```bash
make apply && make seed
```

```
aws_s3_bucket.backups:   Creation complete
aws_dynamodb_table.links: Creation complete
aws_sqs_queue.events:    Creation complete
Apply complete! Resources: 3 added, 0 changed, 0 destroyed.

put:     abc123 -> https://example.com
get:     abc123 -> https://example.com
backup:  s3 key links/abc123.txt
events:  ['created:abc123']
OK
```

> ☝️ Real output from this course's verified environment. OpenTofu created a
> DynamoDB table, an S3 bucket, and an SQS queue **on LocalStack**, then a boto3
> app stored a link, read it back, backed it up to S3, and processed an event off
> the queue — the same code you'd run against real AWS.

---

## The one trick: the endpoint

Everything about LocalStack comes down to a single idea. AWS SDKs and tools let
you override the **endpoint URL**. Point it at LocalStack and the *identical code*
talks to your laptop instead of AWS:

```python
import boto3
# real AWS:        boto3.client("s3")
# LocalStack:      boto3.client("s3", endpoint_url="http://localhost:4566")
```

```bash
# real AWS:   aws s3 ls
# LocalStack: aws --endpoint-url=http://localhost:4566 s3 ls
#   ...or just: awslocal s3 ls    (a wrapper that sets the endpoint for you)
```

That's the whole mental model: **one endpoint, dummy credentials, real AWS API.**

---

## Why it's worth learning this way

- **Free & safe** — no bill, no account, no chance of nuking production.
- **Fast** — local calls, no network latency; spin up and tear down in seconds.
- **Real API surface** — it's the actual AWS protocols, so your boto3/OpenTofu code
  is exactly what you'd ship.
- **Great for tests & CI** — ephemeral AWS in a container is perfect for
  integration tests ([04](04_testing_and_ci/)).

---

## ⚠️ A real gotcha up front

LocalStack's **2026 releases require a free account and an auth token** to start —
the CLI will refuse without `LOCALSTACK_AUTH_TOKEN`. To keep this course
signup-free, we pin the older token-free community image **`localstack:3.8.1`**.
Everything works identically; [04-3](04_testing_and_ci/03_gotchas_and_pro.md) shows
how to use the latest version with a free token if you want it. This is exactly the
kind of thing that bites people — better to know it now.

---

## What you need

- **Docker** running (LocalStack is a container).
- **Python 3.10+** with **boto3**; the **`awslocal`** CLI helper; the **AWS CLI**.
- The [OpenTofu course](../opentofu_iac/) for Section 03 (the `aws` provider).
- **No AWS account, no LocalStack account** (with the pinned image).

---

**Next → [01-1 · What is LocalStack?](01_foundations/01_what_is_localstack.md)**
