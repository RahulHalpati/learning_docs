# 00 · Introduction

> **Level:** Beginner → Intermediate · **Time:** 15 min · **Verified:** 2026-09-01 (Floci latest, Docker 29.7.2)

Learning AWS usually means a credit card, a fear of surprise bills, and slow
network round-trips. **An AWS emulator removes all three.** This course uses
**Floci** — a free, MIT-licensed emulator that runs the AWS APIs in a container
on your machine — so you learn and build against S3, DynamoDB, SQS, and
Lambda for free, offline, and instantly.

---

## What you'll build

The `linkstash` app you met in the [CI/CD](../cicd_github_actions/) and
[OpenTofu](../opentofu_iac/) courses — now **cloud-native**. Its data moves into
AWS services, provisioned with OpenTofu and exercised with the AWS SDK, all on
Floci:

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
> DynamoDB table, an S3 bucket, and an SQS queue **on Floci**, then a boto3
> app stored a link, read it back, backed it up to S3, and processed an event off
> the queue — the same code you'd run against real AWS.

---

## The one trick: the endpoint

Everything about AWS emulation comes down to a single idea. AWS SDKs and tools let
you override the **endpoint URL**. Point it at the emulator and the *identical code*
talks to your laptop instead of AWS:

```python
import boto3
# real AWS:        boto3.client("s3")
# Floci:           boto3.client("s3", endpoint_url="http://localhost:4566")
```

```bash
# real AWS:   aws s3 ls
# Floci:      aws --endpoint-url=http://localhost:4566 s3 ls
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
  integration tests ([04](05_testing_and_ci/)).

---

## ⚠️ Why Floci and not LocalStack?

**LocalStack** invented this category — and its name is still all over job posts —
but in **March 2026 it sunset its free Community edition**: the image now requires
an account and a `LOCALSTACK_AUTH_TOKEN`, the open-source repo was archived, and
the old token-free images get no updates or security patches. **Floci** is the
MIT-licensed drop-in replacement: same port (`4566`), same health endpoint, same
`awslocal` workflow, all services unlocked, no signup, actively maintained.
Everything you learn here maps 1:1 to LocalStack if an employer uses it —
[05-3](05_testing_and_ci/03_gotchas_and_pro.md) tells the full story.

---

## What you need

- **Docker** running (the emulator is a container).
- **Python 3.10+** with **boto3**; the **`awslocal`** CLI helper; the **AWS CLI**.
- The [OpenTofu course](../opentofu_iac/) for Section 03 (the `aws` provider).
- **No AWS account, no emulator account, no auth token** — Floci is free and MIT-licensed.

---

**Next → [01-1 · What is an AWS emulator?](01_foundations/01_what_is_an_aws_emulator.md)**
