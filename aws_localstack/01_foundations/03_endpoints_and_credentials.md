# 01-3 · Endpoints & credentials

> **Level:** Beginner · **Prerequisites:** [01-2 Setup & first service](02_setup_and_first_service.md)
> **Time:** 20 min · **Verified:** 2026-07-16

The whole course rests on one mechanism: **override the endpoint**. Here's how to
do it from each tool, so you can point *anything* at LocalStack — and back at real
AWS by removing one setting.

---

## boto3 (Python SDK)

Pass `endpoint_url`, or read it from an env var so the same code works both ways:

```python
import boto3, os

# explicit
s3 = boto3.client("s3", endpoint_url="http://localhost:4566")

# env-driven (recommended) — the capstone's pattern
s3 = boto3.client("s3", endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None)
```

With `AWS_ENDPOINT_URL=http://localhost:4566` set, calls go to LocalStack; unset,
`endpoint_url=None` and boto3 uses the real AWS defaults. **One env var flips the
whole app** — exactly what [`app/storage.py`](../99_project_linkstash_cloud/app/storage.py)
does.

> Modern AWS SDKs also honour the standard **`AWS_ENDPOINT_URL`** env var directly,
> so often you don't even pass `endpoint_url` — just set the variable.

---

## AWS CLI

Two ways:

```bash
# per-command flag
aws --endpoint-url=http://localhost:4566 s3 ls

# or the wrapper that does it for you
awslocal s3 ls
```

`awslocal` is just `aws` with the endpoint (and dummy creds) injected — use it
interactively; use the explicit flag in scripts where you want it visible.

---

## OpenTofu / Terraform

The `aws` provider takes an `endpoints` block plus a few `skip_*` flags (LocalStack
has no real IAM/account to validate against). From the capstone's
[`infra/main.tf`](../99_project_linkstash_cloud/infra/main.tf):

```hcl
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  endpoints {
    s3       = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
    sqs      = "http://localhost:4566"
  }
}
```

Delete that endpoints/skip block and the identical resources provision to **real
AWS**. (The `tflocal` wrapper automates this block, but writing it once shows
exactly what's happening — [03-1](../03_iac_with_opentofu/01_aws_provider_against_localstack.md).)

---

## Credentials: present but ignored

LocalStack doesn't check credentials, but the SDKs/CLI refuse to run without
*some*. Set dummy values once via env:

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:4566
```

That's the standard LocalStack environment — the capstone `Makefile` exports
exactly these. Region matters (resources are per-region even in LocalStack); the
keys are placeholders.

---

## Recap & next

- ✅ Everything hinges on the **endpoint override**: `endpoint_url` (boto3),
  `--endpoint-url`/`awslocal` (CLI), `endpoints{}` (OpenTofu).
- ✅ Drive it from **`AWS_ENDPOINT_URL`** so the same code targets LocalStack or
  real AWS by one variable.
- ✅ Credentials are **required but ignored** — use `test`/`test`; set a real
  region.

**Self-check:** The capstone's `storage.py` does
`endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None`. Why the `or None`, and
what does it enable?

<details>
<summary>Answer</summary>

If `AWS_ENDPOINT_URL` is unset, `os.environ.get(...)` returns `None`, and passing
`endpoint_url=None` tells boto3 to use its **default (real AWS) endpoints**. So the
*same code* runs against LocalStack when the var is set and against real AWS when
it isn't — no code change to promote from local dev to production.

</details>

**→ Next: [02-1 · S3 (object storage)](../02_core_services/01_s3.md)**
