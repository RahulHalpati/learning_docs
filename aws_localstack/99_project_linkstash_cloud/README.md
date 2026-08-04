# 99 · Capstone — linkstash-cloud

The `linkstash` link shortener, backed by AWS services running on LocalStack:
links in **DynamoDB**, backups in **S3**, events on **SQS**, secret in **Secrets
Manager**, config in **SSM Parameter Store** — provisioned with **OpenTofu** and
exercised with **boto3**. Real AWS SDK + IaC, zero cloud bill.

```
tofu apply → DynamoDB + S3 + SQS + Secrets Manager + SSM on LocalStack (6 resources)
python -m app.demo → load config from AWS, put/get a link, back up to S3, drain an SQS event
pytest → 7 integration tests, green
```

---

## Layout

```
99_project_linkstash_cloud/
├── app/
│   ├── storage.py     # LinkStore: boto3 against DynamoDB + S3 + SQS (endpoint-driven)
│   ├── config.py      # load secret (Secrets Manager) + table name (SSM) at runtime
│   └── demo.py        # end-to-end: load config, put/get/backup/drain demo
├── infra/
│   └── main.tf        # aws provider → LocalStack; DynamoDB + S3 + SQS + Secrets Manager + SSM
├── tests/
│   ├── test_storage.py  # 4 storage integration tests
│   └── test_config.py   # 3 config-from-AWS tests (skip unless AWS_ENDPOINT_URL set)
├── Makefile           # install / up / apply / seed / verify / test / down
└── requirements.txt
```

---

## Quick start

```bash
make install     # boto3, localstack, awslocal, awscli
make up          # docker run localstack/localstack:3.8.1 (token-free community)
make apply       # tofu → DynamoDB + S3 + SQS on LocalStack
make seed        # boto3 demo
make verify      # awslocal lists the resources
make test        # pytest integration tests
make down        # stop LocalStack
```

The `Makefile` exports the standard LocalStack env for you:
`AWS_ENDPOINT_URL=http://localhost:4566`, dummy creds, `us-east-1`.

### Verified output (2026-07-16, LocalStack 3.8.1, OpenTofu v1.12.4)

```
$ tofu apply
aws_secretsmanager_secret.app:         Creation complete
aws_secretsmanager_secret_version.app: Creation complete
aws_s3_bucket.backups:                 Creation complete
aws_dynamodb_table.links:              Creation complete
aws_ssm_parameter.links_table:         Creation complete
aws_sqs_queue.events:                  Creation complete
Apply complete! Resources: 6 added, 0 changed, 0 destroyed.

$ python -m app.demo
config:  secret_key=dev*** (Secrets Manager)  table=links (SSM)
put:     abc123 -> https://example.com
get:     abc123 -> https://example.com
backup:  s3 key links/abc123.txt
events:  ['created:abc123']
OK

$ awslocal dynamodb list-tables      → {"TableNames": ["links"]}
$ awslocal s3 ls                      → linkstash-backups
$ awslocal sqs list-queues            → linkstash-events

$ pytest -q
7 passed
```

---

## The one idea worth remembering

`storage.py` sets `endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None`, and
`infra/main.tf` has an `endpoints{}` block. **Remove those and the identical code +
config run against real AWS.** LocalStack is a target you swap in for dev/test — not
a different way of writing AWS code.

---

## ⚠️ Notes

- **Account requirement:** LocalStack's 2026 CLI needs a free token; this capstone
  pins **`localstack:3.8.1`** to stay signup-free ([04-3](../04_testing_and_ci/03_gotchas_and_pro.md)).
- **Ephemeral:** state is lost when the container stops — `make apply` re-creates
  it. That's ideal for tests.
- **Lambda:** the app runs as a normal process; a serverless variant is the stretch
  exercise in [02-4](../02_core_services/04_lambda_apigateway.md).

→ Course starts at the **[README](../README.md)** → **[00 · Introduction](../00_introduction.md)**.
