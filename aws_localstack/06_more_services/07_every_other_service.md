# 06-7 · The pattern scales: every other service

> **Level:** Intermediate · **Prerequisites:** [06-6 ElastiCache: caching](06_elasticache.md)
> **Time:** 25 min · **Verified:** 2026-09-01 (Floci latest — service list via `/_localstack/health`)

You've now deep-dived about ten services. Floci exposes **~100**. This lesson is
deliberately *not* thirty-four more walkthroughs — because you already know everything you need
to use any of them. The point of the course was the **pattern**; this lesson proves it scales and
hands you a map for the rest.

---

## The universal pattern (it never changes)

Every AWS service you've touched worked the same way, and so do all the others:

1. Point the client at **`http://localhost:4566`** (endpoint override, or `awslocal`, or the
   Terraform provider from [04-1](../04_iac_with_opentofu/01_aws_provider_against_floci.md)).
2. Use the **exact same boto3 / AWS CLI / Terraform calls** you'd use against real AWS.
3. Watch for the occasional **per-service quirk** (like S3 path-style in [03-1](../03_core_services/01_s3.md)) — they're rare and documented.

That's it. "Learn service X on the emulator" = "look up X's normal boto3/CLI calls and prefix the
endpoint." There is no emulator-specific API to memorize per service.

---

## What's available in *your* emulator

Don't guess the list — ask the running container. This is the health endpoint (the JSON you may
have already seen):

```bash
curl -s http://localhost:4566/_localstack/health | jq '.services'
# or, with the optional CLI:
floci status
```

`"running"` means the emulator answers that API; the set differs by version, and a
few services are **stubs** (canned responses, no real behaviour — e.g. Bedrock
Runtime, Textract, Transcribe). The matrix at [floci.io/aws](https://floci.io/aws/#services)
says which. Check before assuming a service is testable locally.

---

## The map: the rest of the catalog, by job

The ones this course deep-dived are marked ✅ — the rest are "same pattern, reach for when needed":

| Area | Services | For |
|---|---|---|
| Compute | **ec2**, ✅lambda | VMs; serverless functions |
| Storage / data | ✅s3, ✅dynamodb, redshift, **es/opensearch** | objects; NoSQL; warehouse; search |
| Messaging | ✅sqs, ✅sns, ✅eventbridge(events), **ses** | queues; pub/sub; event bus; email |
| Streaming | **kinesis**, **firehose** | real-time streams; stream→store delivery |
| Security | ✅iam, ✅sts, ✅kms, ✅secretsmanager, acm | identity; encryption keys; secrets; TLS certs |
| Config / ops | ✅ssm, cloudformation, config, scheduler, swf | params; native IaC; compliance; cron; workflows |
| Observability | ✅cloudwatch, ✅logs | metrics/alarms; log aggregation |
| Networking | route53, route53resolver | DNS |
| Orchestration | ✅stepfunctions | state-machine workflows |
| ML | transcribe (stub), bedrock-runtime (stub) | speech-to-text; LLMs — stubs: wire-test only |

---

## A few quick ones (proof it's the same pattern)

Not full lessons — just enough to show each is "normal AWS, local endpoint":

```bash
# Kinesis — a stream, then put a record (event ingestion)
awslocal kinesis create-stream --stream-name clicks --shard-count 1
awslocal kinesis put-record --stream-name clicks --partition-key u1 --data '{"slug":"abc"}'

# SES — verify a sender, then send (transactional email)
awslocal ses verify-email-identity --email-address noreply@linkstash.dev
awslocal ses send-email --from noreply@linkstash.dev \
  --destination ToAddresses=user@example.com \
  --message 'Subject={Data=Hi},Body={Text={Data=Welcome}}'
```

Same three-step pattern every time. Once it clicks, the "100 services" stop being 100 things to
learn and become one thing you already know.

---

## Why the course stops here (YAGNI, on purpose)

Ten services deep + the pattern beats thirty-four shallow walkthroughs you'd forget. You learn a
new service the day a project needs it — in an afternoon, because the pattern's identical. Two
honest caveats when you do:

- **Fidelity varies by service.** Core services (S3, SQS, DynamoDB, Lambda) are high-fidelity;
  edge services may mock behaviour (e.g. KMS may not do *real* crypto — see [06-3](03_kms.md); some are
  outright stubs). Check the health endpoint and, for anything security- or correctness-critical,
  validate against real AWS — the same lesson as IAM enforcement in [02-1](../02_iam_and_access/01_access_model_iam_sts.md).
- **`awslocal` is just `aws` with the endpoint set.** Everything you write here is real AWS CLI —
  it transfers 1:1 to production, which is the whole reason this course reinforces your AWS depth.

---

## Recap & next

- ✅ Every Floci service uses the **same pattern**: endpoint at `:4566`, normal
  boto3/CLI/Terraform, watch for rare per-service quirks.
- ✅ Ask **`/_localstack/health`** what's available in your version/edition — don't assume.
- ✅ The map groups the rest by job; Kinesis/Firehose/SES are one-liners, not lessons (KMS and CloudWatch earned their own: 06-3, 06-4).
- ✅ Deep on ten + the pattern > shallow on thirty-four; **check fidelity** and validate
  security-critical behaviour on real AWS.

## Exercise

linkstash needs every click streamed for later analytics. Outline the **Kinesis** steps on
Floci — and name what you'd still verify on real AWS.

<details>
<summary>Answer</summary>

Steps: `kinesis create-stream --stream-name clicks --shard-count 1` → `put-record` per click
(partition key = the user or slug so related records land on one shard) → read with
`get-shard-iterator` + `get-records`, or attach **Firehose** to land them in S3. Verify with
`describe-stream`.
**What Floci doesn't prove:** real sharding/throughput behaviour, iterator-age and
backpressure under load, and IAM permissions on the stream. You've verified your *wiring and
code path*; validate scale and access on real AWS — the same create-vs-enforce gap as IAM.

</details>

**→ Next: [06-8 · Cost & the Well-Architected Framework](08_cost_and_well_architected.md)** — the other
half of access control: what can reach what on the network.
