# 06-1 · Config & secrets — Secrets Manager & SSM Parameter Store

> **Level:** Intermediate · **Prerequisites:** [03-2 DynamoDB](../03_core_services/02_dynamodb.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (LocalStack 3.8.1; runs unchanged on Floci)

The [Secure Code Audit](../../secure_code_audit/) course flagged hardcoded secrets
as a vulnerability. AWS's answer is **Secrets Manager** (for secrets) and **SSM
Parameter Store** (for plain config) — both free in Floci, and both now wired
into the capstone.

---

## Two stores, one idea: config lives outside code

| | Secrets Manager | SSM Parameter Store |
|---|---|---|
| For | passwords, API keys, tokens | non-secret config (URLs, names, flags) |
| Cost (real AWS) | per secret / month | free tier generous |
| Extras | rotation, versioning | hierarchical `/paths`, `SecureString` too |
| Use for | the app's `secret_key` | the DynamoDB table name |

Rule of thumb: **secret → Secrets Manager; plain config → SSM**. (SSM can also hold
secrets as `SecureString`, but Secrets Manager adds rotation and is purpose-built.)

---

## SSM Parameter Store

```bash
awslocal ssm put-parameter --name /demo/greeting --value "hello" --type String
awslocal ssm get-parameter --name /demo/greeting --query 'Parameter.Value' --output text
```

Verified:

```
hello
```

Parameters are organised as **`/paths`** (`/linkstash/links-table`), so you can
fetch a whole app's config by prefix with `get-parameters-by-path`.

---

## Secrets Manager

```bash
awslocal secretsmanager create-secret --name demo/api --secret-string "s3cr3t"
awslocal secretsmanager get-secret-value --secret-id demo/api --query 'SecretString' --output text
```

Verified:

```
s3cr3t
```

---

## In the capstone

The infra now provisions both ([`infra/main.tf`](../99_project_linkstash_cloud/infra/main.tf)):

```hcl
resource "aws_secretsmanager_secret"          "app" { name = "linkstash/secret-key" }
resource "aws_secretsmanager_secret_version"  "app" {
  secret_id     = aws_secretsmanager_secret.app.id
  secret_string = "dev-secret-rotate-me"
}
resource "aws_ssm_parameter" "links_table" {
  name  = "/linkstash/links-table"
  type  = "String"
  value = aws_dynamodb_table.links.name   # resolved from the resource, not hardcoded
}
```

And [`app/config.py`](../99_project_linkstash_cloud/app/config.py) loads them at
runtime:

```python
def load_secret_key():
    return client("secretsmanager").get_secret_value(SecretId=SECRET_NAME)["SecretString"]

def load_table_name():
    return client("ssm").get_parameter(Name=TABLE_PARAM)["Parameter"]["Value"]
```

Verified in the demo (secret masked, table name from SSM):

```
config:  secret_key=dev*** (Secrets Manager)  table=links (SSM)
```

The `secret_key` that the code-audit course caught hardcoded in a Flask app now
comes from Secrets Manager — same app, secret out of the source. Note the SSM
parameter's value is `aws_dynamodb_table.links.name`, so config and infrastructure
can't drift.

---

## Recap & next

- ✅ **Secrets Manager** for secrets (rotation/versioning); **SSM Parameter Store**
  for plain config (`/paths`).
- ✅ Load both at **runtime** — the fix for the hardcoded-secret vuln from the
  audit course, done the AWS way.
- ✅ The capstone provisions and reads both (verified `secret_key=dev*** table=links`).

## Exercise

Add a second SSM parameter `/linkstash/backup-bucket` set to the S3 bucket name, and
have `config.py` load it. Why source the bucket name from SSM rather than hardcode
`"linkstash-backups"` in the app?

<details>
<summary>Solution</summary>

```hcl
resource "aws_ssm_parameter" "backup_bucket" {
  name = "/linkstash/backup-bucket"
  type = "String"
  value = aws_s3_bucket.backups.id
}
```

Sourcing it from SSM (set to `aws_s3_bucket.backups.id`) means the app always uses
the *actual* provisioned bucket name — if the infra changes it (per environment,
say), the app follows automatically with no code change and no drift between
config and reality.

</details>

**→ Next: [06-2 · Events & orchestration](02_eventbridge_and_stepfunctions.md)**
