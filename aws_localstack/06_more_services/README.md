# 06 · More AWS services

The core four (S3/DynamoDB/SQS/Lambda) get you far, but real systems lean on
config, events, encryption, and observability — plus the two data stores every
backend eventually needs: a relational database and a cache. All free and
verified against Floci here.

| # | Module | Services | You'll be able to… |
|---|---|---|---|
| 06-1 | [Config & secrets](01_secrets_and_ssm.md) | Secrets Manager, SSM Parameter Store | Load secrets/config from AWS instead of code |
| 06-2 | [Events & orchestration](02_eventbridge_and_stepfunctions.md) | EventBridge, Step Functions | Route events on a bus and orchestrate multi-step workflows |
| 06-3 | [Encryption at rest: KMS](03_kms.md) | KMS | Manage keys and encrypt S3/secrets with a CMK (compliance work) |
| 06-4 | [Observability: CloudWatch & Logs](04_cloudwatch_logs.md) | CloudWatch, Logs | Read your app in prod: log groups, metrics, alarms, retention |
| 06-5 | [RDS: a real relational database](05_rds.md) | RDS (Postgres) | Provision a real Postgres instance and connect an app to it |
| 06-6 | [ElastiCache: caching](06_elasticache.md) | ElastiCache (Valkey/Redis) | Add a cache-aside layer in front of DynamoDB |
| 06-7 | [The pattern scales](07_every_other_service.md) | Kinesis, Firehose, SES, Redshift, … | Use any of the ~100 Floci services from the one pattern you know |
| 06-8 | [Cost & the Well-Architected Framework](08_cost_and_well_architected.md) | Cost Explorer, Budgets | Answer "how would you cut this AWS bill?" with real levers |

> Identity moved to the front of the course — see **[02 · IAM & access](../02_iam_and_access/README.md)**.

**Next → [06-1 · Config & secrets](01_secrets_and_ssm.md)**
