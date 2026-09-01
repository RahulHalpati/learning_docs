# 03-2 · DynamoDB (NoSQL)

> **Level:** Beginner · **Prerequisites:** [03-1 S3](01_s3.md)
> **Time:** 30 min · **Verified:** 2026-07-16 (LocalStack 3.8.1; runs unchanged on Floci) — GSI query + conditional-write rejection re-verified 2026-09-01

**DynamoDB** is AWS's managed NoSQL key-value/document store — fast, serverless,
scales without you managing servers. In the capstone it's the source of truth for
links (`slug → url`).

---

## Concepts

- **Table** — a collection of items, defined by a **primary key**.
- **Item** — a row: a set of attributes (like a JSON object).
- **Primary key** — a **partition (hash) key**, optionally plus a **sort key**.
  The capstone table `links` uses `slug` (string) as the hash key.
- **Billing** — `PAY_PER_REQUEST` (on-demand) means no capacity planning; perfect
  for Floci and small apps.

---

## Create a table

With `awslocal`:

```bash
awslocal dynamodb create-table \
  --table-name links \
  --attribute-definitions AttributeName=slug,AttributeType=S \
  --key-schema AttributeName=slug,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

Verified it exists:

```
$ awslocal dynamodb list-tables
{"TableNames": ["links"]}
```

(In the capstone you create it declaratively with OpenTofu — [04-1](../04_iac_with_opentofu/01_aws_provider_against_floci.md) — not by hand.)

---

## Read & write with boto3

The capstone uses the higher-level `resource` interface ([`storage.py`](../99_project_linkstash_cloud/app/storage.py)):

```python
table = boto3.resource("dynamodb", endpoint_url=...).Table("links")

def put(self, slug, url):
    table.put_item(Item={"slug": slug, "url": url, "created": int(time.time())})

def get(self, slug):
    item = table.get_item(Key={"slug": slug}).get("Item")
    return item["url"] if item else None
```

Verified round-trip from the demo (`put` then `get`):

```
put:     abc123 -> https://example.com
get:     abc123 -> https://example.com
```

And the raw item, via the CLI:

```
$ awslocal dynamodb get-item --table-name links --key '{"slug":{"S":"abc123"}}'
{"Item":{"slug":{"S":"abc123"},"url":{"S":"https://example.com"},"created":{"N":"1784195823"}}}
```

Notice the CLI shows DynamoDB's **typed** format (`{"S": ...}` string, `{"N": ...}`
number); the boto3 `resource` interface hides that and gives you plain Python
values — which is why apps prefer it.

---

## Query vs Scan

- **`get_item`** — fetch one item by full key (fast, cheap). What the capstone does.
- **`query`** — fetch a range by partition key (+ sort-key condition) (fast).
- **`scan`** — read the whole table and filter (slow, expensive) — avoid at scale.

Model your keys so you can `get`/`query`, not `scan`. That's the core of DynamoDB
data modelling.

---

## Querying by something other than the partition key: GSI

`get_item`/`query` only work by the table's own key. Need to look items up by
a *different* attribute — say, find every link a given `owner` created? A
**Global Secondary Index (GSI)** is a second, automatically-maintained index
over the same items with its own key:

```bash
awslocal dynamodb create-table --table-name links \
  --attribute-definitions AttributeName=slug,AttributeType=S AttributeName=owner,AttributeType=S \
  --key-schema AttributeName=slug,KeyType=HASH \
  --global-secondary-indexes '[{"IndexName":"owner-index","KeySchema":[{"AttributeName":"owner","KeyType":"HASH"}],"Projection":{"ProjectionType":"ALL"}}]' \
  --billing-mode PAY_PER_REQUEST
```

```python
resp = table.query(IndexName="owner-index",
                    KeyConditionExpression=Key("owner").eq("alice"))
```

Verified: querying `owner-index` for `alice` returned both her items, by
index — no `scan`. This is the real answer to **single-table design** (the
DynamoDB modelling philosophy you'll hear about in interviews): one table,
multiple GSIs, each shaped for one access pattern your app actually needs —
figure out your queries *first*, then design keys/GSIs to serve them, rather
than modelling data the relational way and fighting DynamoDB afterward.

## Preventing a race condition: conditional writes

The capstone's `put()` will happily overwrite an existing slug — two users
requesting the same custom slug at the same instant both "succeed," and one
silently clobbers the other. A **conditional write** makes the second one
fail instead:

```python
try:
    table.put_item(Item={"slug": "abc123", "url": "https://example.com"},
                    ConditionExpression="attribute_not_exists(slug)")
except ClientError as e:
    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
        raise SlugTakenError("abc123")
```

Verified: a first `put_item` with this condition succeeds; an identical second
call for the same `slug` raises `ConditionalCheckFailedException` — DynamoDB
itself enforces the check atomically, so there's no race window between "check
if it exists" and "write it" the way a naive `get` then `put` would have.
This is the general pattern for **any** "only if" write — optimistic locking
with a version number uses the same `ConditionExpression` mechanism.

---

## Access & IAM

Who can touch the table is an **identity policy** on the caller's role — least privilege
means naming the actions *and* the table ARN, never `*`:

```json
{ "Effect": "Allow",
  "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
  "Resource": "arn:aws:dynamodb:*:*:table/links" }
```

Author it here; **Floci won't enforce it** (every call passes), so validate
allow/deny on real AWS. Full treatment: [05-4 · IAM in practice](../02_iam_and_access/02_roles_and_policies_per_service.md).

---

## Recap & next

- ✅ **DynamoDB = tables of items** with a **partition key** (+ optional sort key);
  `PAY_PER_REQUEST` needs no capacity planning.
- ✅ **`put_item`/`get_item`** via the boto3 `resource` interface (plain Python
  values) — verified round-trip in the capstone.
- ✅ Prefer **`get`/`query`** over **`scan`**; the raw API uses a typed format
  (`{"S":...}`) the resource interface hides.
- ✅ **GSI** answers "query by something other than the key" — the basis of
  single-table design; **conditional writes** (`ConditionExpression`) close race
  conditions atomically, verified with a real rejected duplicate write.

## Exercise

Add a `delete(slug)` method and a `list_all()` that returns every slug. Which
DynamoDB operation should `list_all` use, and why is it something you'd avoid on a
large real table?

<details>
<summary>Solution</summary>

```python
def delete(self, slug): self.ddb.delete_item(Key={"slug": slug})
def list_all(self): return [i["slug"] for i in self.ddb.scan().get("Items", [])]
```

`list_all` must **`scan`** (no key to query by), which reads the entire table — fine
for a demo, but expensive and slow on a large table. On real AWS you'd add a
secondary index or restructure keys to avoid full scans.

</details>

**→ Next: [03-3 · SQS & SNS](03_sqs_sns.md)**
