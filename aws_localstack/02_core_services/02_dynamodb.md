# 02-2 · DynamoDB (NoSQL)

> **Level:** Beginner · **Prerequisites:** [02-1 S3](01_s3.md)
> **Time:** 25 min · **Verified:** 2026-07-16 (LocalStack 3.8.1)

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
  for LocalStack and small apps.

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

(In the capstone you create it declaratively with OpenTofu — [03-1](../03_iac_with_opentofu/01_aws_provider_against_localstack.md) — not by hand.)

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

## Recap & next

- ✅ **DynamoDB = tables of items** with a **partition key** (+ optional sort key);
  `PAY_PER_REQUEST` needs no capacity planning.
- ✅ **`put_item`/`get_item`** via the boto3 `resource` interface (plain Python
  values) — verified round-trip in the capstone.
- ✅ Prefer **`get`/`query`** over **`scan`**; the raw API uses a typed format
  (`{"S":...}`) the resource interface hides.

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

**→ Next: [02-3 · SQS & SNS](03_sqs_sns.md)**
