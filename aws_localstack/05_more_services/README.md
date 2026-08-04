# 05 · More AWS services

The core four (S3/DynamoDB/SQS/Lambda) get you far, but real systems lean on
config, events, orchestration, and identity. These are all free in Community and
verified against LocalStack here.

| # | Module | Services | You'll be able to… |
|---|---|---|---|
| 05-1 | [Config & secrets](01_secrets_and_ssm.md) | Secrets Manager, SSM Parameter Store | Load secrets/config from AWS instead of code |
| 05-2 | [Events & orchestration](02_eventbridge_and_stepfunctions.md) | EventBridge, Step Functions | Route events on a bus and orchestrate multi-step workflows |
| 05-3 | [Identity: IAM & STS](03_iam_and_sts.md) | IAM, STS | Model roles/policies (and know LocalStack's IAM caveat) |

**Next → [05-1 · Config & secrets](01_secrets_and_ssm.md)**
