# 06-3 · Encryption at rest: KMS

> **Level:** Intermediate · **Prerequisites:** [06-1 Config & secrets](01_secrets_and_ssm.md)
> **Time:** 25 min · **Verified:** 2026-08-21 (LocalStack 3.8.1; runs unchanged on Floci) — with a fidelity caveat

06-1 got secrets *out of the code*. This lesson is the layer under that: **what
actually encrypts them**. **KMS** (Key Management Service) is AWS's managed key
store — it holds the keys, does the crypto, and logs every use, so you never write
key-handling code yourself.

If you want to work in healthcare or fintech, this is not optional trivia:
"encrypted at rest with a customer-managed key" is a line item in HIPAA, PCI-DSS
and SOC 2 audits, and someone has to be able to explain how it's wired. That
someone is in demand.

---

## Envelope encryption in one paragraph

You don't encrypt your data *with* the KMS key. KMS generates a short-lived **data
key**, your data is encrypted with that (fast, local, symmetric), and the data key
itself is encrypted by the **CMK** (customer master key) and stored next to the
ciphertext. To read the data, a service asks KMS to decrypt the data key, uses it,
and throws it away. That's **envelope encryption**: the CMK never leaves KMS, big
payloads never travel to KMS, and revoking access to one key ARN instantly locks
everything wrapped by it.

Why not hand-roll it? Because key generation, storage, rotation, per-use audit
logging and "delete the key and the data is unreadable" are exactly the things
homegrown crypto gets wrong. KMS is the boring correct answer.

---

## Create a key + alias

```bash
# a key is created first; it has only an opaque ID
KEY_ID=$(awslocal kms create-key --query KeyMetadata.KeyId --output text)

# an alias is the human-readable handle you use everywhere else
awslocal kms create-alias --alias-name alias/linkstash --target-key-id "$KEY_ID"
awslocal kms describe-key --key-id alias/linkstash --query KeyMetadata.Arn --output text
```

Verified:

```
$ echo $KEY_ID
b1e7f3a2-0c4d-4f19-9a3e-5c8d21ab7f60
$ awslocal kms describe-key --key-id alias/linkstash --query KeyMetadata.Arn --output text
arn:aws:kms:us-east-1:000000000000:key/b1e7f3a2-0c4d-4f19-9a3e-5c8d21ab7f60
```

Always reference the **alias** (`alias/linkstash`) in config and IaC, never the raw
UUID — aliases survive key rotation and read sanely in a policy review.

---

## Direct encrypt / decrypt

KMS will encrypt small payloads (≤4 KB) directly — useful for a token or a single
field, not for files.

```bash
# encrypt: CiphertextBlob comes back base64-encoded in JSON output
awslocal kms encrypt --key-id alias/linkstash --plaintext "$(echo -n 'hunter2' | base64)" \
  --query CiphertextBlob --output text > ct.b64

# decrypt: the CLI wants raw bytes, so decode first and pass with fileb://
base64 -d ct.b64 > ct.bin
awslocal kms decrypt --ciphertext-blob fileb://ct.bin --query Plaintext --output text | base64 -d
```

Verified:

```
$ cat ct.b64
AQICAHi3k0zGkVQ9wR2xTk4pV0m5uYQ7... (truncated)
$ awslocal kms decrypt --ciphertext-blob fileb://ct.bin --query Plaintext --output text | base64 -d
hunter2
```

The base64 double-handling trips everyone once: `--plaintext` and `Plaintext` are
base64 in JSON, while `--ciphertext-blob` wants **raw bytes** — hence `fileb://`.
In boto3 (below) this is invisible; the SDK passes bytes.

---

## S3 SSE-KMS — the one you'll actually ship

The real-world use of KMS is telling *another service* to encrypt with your key.
For S3 that's **SSE-KMS**, and the good pattern is a **bucket default**, so nobody
can forget the flag on a single upload.

```bash
awslocal s3api put-bucket-encryption --bucket linkstash-backups \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "alias/linkstash"
      },
      "BucketKeyEnabled": true
    }]
  }'
awslocal s3api get-bucket-encryption --bucket linkstash-backups
```

Verified:

```json
{
  "ServerSideEncryptionConfiguration": {
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "alias/linkstash"
      },
      "BucketKeyEnabled": true
    }]
  }
}
```

Per-object, if you need a different key for one path:

```bash
awslocal s3api put-object --bucket linkstash-backups --key links/abc123.txt --body abc.txt \
  --server-side-encryption aws:kms --ssekms-key-id alias/linkstash
awslocal s3api head-object --bucket linkstash-backups --key links/abc123.txt \
  --query '[ServerSideEncryption,SSEKMSKeyId]'
# → [ "aws:kms", "arn:aws:kms:us-east-1:000000000000:key/b1e7f3a2-..." ]
```

This is the missing piece in [03-1 S3](../03_core_services/01_s3.md): linkstash
backs up every link to `s3://linkstash-backups/links/<slug>.txt`. Those are user
URLs. With the bucket default set, `storage.py` doesn't change a line and every
backup lands encrypted under `alias/linkstash` — and `BucketKeyEnabled` means S3
caches one bucket-level data key instead of calling KMS per object (on real AWS,
that's a real bill difference).

---

## Secrets Manager is KMS underneath

Every Secrets Manager secret is already encrypted with a KMS key — by default the
AWS-managed `aws/secretsmanager` key. Point it at your own CMK when an auditor
wants to see a customer-managed key and an access trail you control:

```bash
awslocal secretsmanager create-secret --name linkstash/secret-key \
  --secret-string "dev-secret-rotate-me" --kms-key-id alias/linkstash
```

Same for the `SecureString` parameters from [06-1](01_secrets_and_ssm.md) — `ssm
put-parameter --type SecureString --key-id alias/linkstash`. The upside of a CMK:
you can revoke `kms:Decrypt` and the secret becomes unreadable *even to principals
who still have `secretsmanager:GetSecretValue`*.

---

## boto3

```python
import boto3, base64

kms = boto3.client("kms", endpoint_url="http://localhost:4566", region_name="us-east-1")

# bytes in, bytes out — no base64 juggling in the SDK
blob = kms.encrypt(KeyId="alias/linkstash", Plaintext=b"hunter2")["CiphertextBlob"]
plain = kms.decrypt(CiphertextBlob=blob)["Plaintext"]      # KeyId not needed: it's in the blob
assert plain == b"hunter2"

# store the ciphertext anywhere (DynamoDB attribute, S3 object) — base64 for text fields
print(base64.b64encode(blob).decode()[:32], "...")
```

Note `decrypt` needs no `KeyId`: the ciphertext blob carries which key made it.
That's also why you can't decrypt without permission on *that* key.

---

## Key policies: resource-based, on a key

[02-2](../02_iam_and_access/02_roles_and_policies_per_service.md) split policies
into **identity-based** (attached to a role) and **resource-based** (attached to
the thing). A KMS key is the second kind, and stricter than most: a key's
**key policy** is the primary authority — an IAM policy granting `kms:*` does
nothing if the key policy doesn't also allow that principal.

Least privilege for linkstash: the Lambda role only ever *reads* backups, so it
gets **`kms:Decrypt` on that key ARN and nothing else**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "AdminsManageTheKey",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::000000000000:role/linkstash-admin" },
      "Action": "kms:*",
      "Resource": "*" },
    { "Sid": "AppDecryptsOnly",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::000000000000:role/linkstash-lambda" },
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "*" }
  ]
}
```

(`"Resource": "*"` inside a key policy means "this key" — it's the one place that
wildcard isn't a smell.) Apply it with `awslocal kms put-key-policy --key-id
alias/linkstash --policy-name default --policy file://key-policy.json`.

Two things worth knowing before an interview: writing an object with SSE-KMS needs
**`kms:GenerateDataKey`** (not `Encrypt`) because S3 asks for a data key; and
locking yourself out is real — a key policy with no admin statement is
unrecoverable, which is why the first statement above exists.

---

## ⚠️ The fidelity caveat

This is the same create-vs-enforce line the course keeps drawing, and KMS is where
it's widest. On Floci you can create keys and aliases, set bucket
encryption, and read all of it back — the **API shape and the wiring are real**.
What Floci does *not* reliably give you:

| You verified locally | You have **not** verified |
|---|---|
| the key/alias exists, `describe-key` returns it | that stored bytes are genuinely encrypted with it |
| `get-bucket-encryption` returns your SSE-KMS rule | that S3 refuses/encrypts accordingly under load |
| `put-key-policy` accepted your document | that the policy **denies** anyone — Floci doesn't enforce |
| `decrypt` round-trips your plaintext | that it's real KMS crypto rather than a stand-in |

So: treat local KMS as a **wiring test** — does my IaC produce the right
configuration, does my code call the right API with the right key. Encryption
actually happening, and key access actually being denied, must be validated on real
AWS (or Pro). It's the exact rule from
[02-1's enforcement caveat](../02_iam_and_access/01_access_model_iam_sts.md#️-the-caveat-community-doesnt-enforce-iam),
extended from IAM to crypto.

---

## Recap & next

- ✅ **Envelope encryption**: a short-lived **data key** encrypts the data; the
  **CMK** encrypts the data key and never leaves KMS.
- ✅ Create a key, then always address it by **alias** (`alias/linkstash`) — aliases
  survive rotation.
- ✅ **SSE-KMS as a bucket default** (`put-bucket-encryption` + `BucketKeyEnabled`)
  encrypts every linkstash backup with zero app changes; per-object flags for
  exceptions.
- ✅ Secrets Manager and SSM `SecureString` are KMS underneath — swap in your CMK to
  own the audit trail and the revoke switch.
- ✅ A **key policy** is resource-based and *primary*: least privilege is
  `kms:Decrypt` (+ `GenerateDataKey` to write) scoped to that key, plus an admin
  statement so you can't lock yourself out.
- ✅ Floci proves the **configuration**, not the **cryptography or the denial** —
  validate both on real AWS.

## Exercise

Compliance says linkstash must encrypt its S3 backups with a **customer-managed
key**, and the app's Lambda must be able to read them but never delete the key.
Outline the steps — and name precisely what your Floci run does *not* prove.

<details>
<summary>Answer</summary>

**Steps:**

1. `kms create-key`, then `kms create-alias --alias-name alias/linkstash` — a CMK
   you own (not the AWS-managed `aws/s3` key), referenced by alias.
2. `s3api put-bucket-encryption` on `linkstash-backups` with
   `SSEAlgorithm=aws:kms`, `KMSMasterKeyID=alias/linkstash`, `BucketKeyEnabled=true`
   — a bucket default, so no upload can skip it.
3. Key policy: an admin statement (`kms:*` for the admin role) plus
   `kms:Decrypt` + `kms:GenerateDataKey` for `role/linkstash-lambda` only. No
   `kms:ScheduleKeyDeletion`, no `kms:PutKeyPolicy` for the app role.
4. Lambda's identity policy also needs `kms:Decrypt`/`kms:GenerateDataKey` on the
   key ARN alongside its `s3:GetObject`/`PutObject` — both sides must allow.
5. Put it all in OpenTofu (`aws_kms_key`, `aws_kms_alias`,
   `aws_s3_bucket_server_side_encryption_configuration`) so it's reproducible.
6. Verify locally: `get-bucket-encryption` returns the rule, `head-object` reports
   `ServerSideEncryption: aws:kms` and your key ARN.

**What Floci does NOT prove:** that the objects are really encrypted with that
CMK (Floci may not perform genuine KMS crypto); that the key policy *denies*
anything — it isn't enforced, so a Lambda missing `kms:Decrypt` still reads happily
here and fails with `AccessDenied`/`KMSAccessDeniedException` in production; that
deleting/disabling the key makes backups unreadable; and any real cost or latency
behaviour of `BucketKeyEnabled`. All of that needs real AWS or Pro.

</details>

**→ Next: [06-4 · Observability: CloudWatch & Logs](04_cloudwatch_logs.md)**
