# 06-8 · Cost & the Well-Architected Framework

> **Level:** Intermediate · **Prerequisites:** [06-7 The pattern scales](07_every_other_service.md)
> **Time:** 20 min · **No hands-on** — this is judgment, not an API. Nothing here needs Floci; the concepts apply identically on real AWS.

"How would you reduce this AWS bill?" is one of the most common AWS interview
questions at any level, and it's the one place this course's local-emulator
approach can't give you a bill to look at. So this lesson works from real AWS
pricing mechanics and the architecture you already built in the capstone.

## The five things that actually drive an AWS bill

Ignore the 200-service pricing pages — almost every real bill comes down to
five levers:

1. **Compute running when nothing's happening.** An EC2 instance or a
   provisioned-capacity resource costs the same at 2am with zero traffic as at
   peak. This is *the* reason serverless (Lambda, DynamoDB on-demand) exists —
   the capstone's `PAY_PER_REQUEST` DynamoDB table ([03-2](../03_core_services/02_dynamodb.md))
   already reflects this: zero traffic, zero cost.
2. **Data transfer, especially out to the internet.** Data *into* AWS is free;
   data *out* isn't, and cross-region/cross-AZ transfer adds up in ways a
   single-region demo never shows you. A CDN (CloudFront) in front of S3 turns
   repeated egress into one cached copy.
3. **Storage class mismatch.** S3 Standard for data nobody's read in six
   months is pure waste — **lifecycle policies** transition it to
   Infrequent Access or Glacier automatically. Same data, same durability,
   a fraction of the cost, zero code change.
4. **Over-provisioned instances.** The single most common finding in a real
   cost review: an RDS/EC2 instance sized for a launch-day traffic spike that
   never came back down. This is **vertical scaling's** dark side from the
   scaling discussion — right-sizing (or a Multi-AZ read replica instead of
   one giant instance) usually beats "just make it bigger."
5. **Forgotten resources.** Untagged, unattached EBS volumes, idle load
   balancers, an old NAT Gateway (charged per hour *and* per GB, one of the
   most commonly forgotten line items) — the boring answer to "where did the
   spike come from" is usually "something nobody's using is still running."

**The honest, senior answer to "how do you cut costs":** you can't optimize
what you can't see. Cost Explorer + tagging *every* resource by
team/project/environment is the actual first move, before touching any single
service — otherwise you're guessing which 5% of spend to attack.

## The AWS Well-Architected Framework — six pillars

AWS's own framework for evaluating an architecture, genuinely used in
enterprise architecture reviews (and referenced in interviews at exactly the
kind of "Enterprise Platform" team a job post might describe):

| Pillar | The question it asks | You've already seen this in... |
|---|---|---|
| **Operational Excellence** | Can you observe, deploy, and recover safely? | [06-4 CloudWatch/Logs](04_cloudwatch_logs.md) |
| **Security** | Least privilege, encryption, no long-lived secrets? | [02 IAM](../02_iam_and_access/README.md), [06-3 KMS](03_kms.md) |
| **Reliability** | Does it survive an AZ failure, a dependency outage? | [07 Networking](../07_networking_and_compute/README.md) (Multi-AZ) |
| **Performance Efficiency** | Right service/size for the workload? | [06-5 RDS vs DynamoDB](05_rds.md) tradeoff table |
| **Cost Optimization** | Are you paying for what you use, not what you provisioned? | this lesson |
| **Sustainability** | Minimizing the resources consumed for the same outcome | (often the newest, least-asked in interviews) |

Notice cost is **one pillar of six**, not the whole framework — a common
mistake is treating "make it cheaper" as the only lens, when the real
job is the *tradeoff* between all six (the cheapest architecture is often the
least reliable one).

## Applying this to the capstone

`linkstash-cloud` already makes several Well-Architected-aligned choices worth
being able to explain out loud:

- **DynamoDB on-demand** (Cost + Performance Efficiency) — no idle capacity to
  pay for, scales to the actual request rate.
- **Secrets Manager, not a hardcoded password** (Security) — from [06-1](01_secrets_and_ssm.md).
- **SQS between the write and the event consumer** (Reliability) — a crashed
  consumer doesn't lose events; they wait in the queue ([03-3](../03_core_services/03_sqs_sns.md)).

What it *doesn't* do, because it's a learning capstone, not production: no
Multi-AZ, no CloudFront in front of S3, no budget alerts. Naming that gap
yourself in an interview — "here's what I'd add for production, and why I
didn't build it into a demo" — reads better than pretending the demo is
production-grade.

## Recap & next

- ✅ Five real cost levers: **idle compute, data egress, storage class,
  over-provisioning, and forgotten resources** — in that rough order of
  how often they're the actual answer.
- ✅ You can't optimize what you can't see — **tagging + Cost Explorer** comes
  before any specific fix.
- ✅ **Well-Architected = six pillars**, cost is one of them; the real skill is
  the tradeoff between them, not minimizing cost alone.

## Exercise

An interviewer asks: "Our S3 bill tripled last month and nobody changed the
app." Walk through how you'd actually find the cause.

<details>
<summary>Answer</summary>

Check **Cost Explorer** filtered to S3, grouped by usage type, to see whether
it's storage volume, request count, or data transfer that jumped — they have
completely different causes. Storage volume up → something's writing more
data than before (a logging bug writing duplicates, a lifecycle policy that
stopped running). Request count up → a retry loop or a misconfigured client
polling too often. Data transfer up → something's now serving objects
publicly/cross-region that used to be served from a cache or CDN. The point of
the answer isn't guessing right — it's **the diagnostic order**: bill →
Cost Explorer breakdown → which dimension moved → then investigate that
specific cause, not the S3 console in general.

</details>

**→ Next: [07 · Networking & compute](../07_networking_and_compute/README.md)**
