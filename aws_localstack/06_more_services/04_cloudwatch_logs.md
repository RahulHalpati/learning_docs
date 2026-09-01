# 06-4 · Observability: CloudWatch & Logs

> **Level:** Intermediate · **Prerequisites:** [06-3 Encryption at rest: KMS](03_kms.md)
> **Time:** 25 min · **Verified:** 2026-08-21 (LocalStack 3.8.1; runs unchanged on Floci)

In production you can't attach a debugger, add a `print` and re-run, or ask the
container what it was thinking. **Logs and metrics are all you have.** CloudWatch is
where both live, so this lesson is really about one skill: *how you read your app in
prod.*

---

## Logs: group → stream → events

Three nouns, in order:

| Noun | Is | Example |
|---|---|---|
| **Log group** | one logical source, holds retention + permissions | `/linkstash/app`, `/aws/lambda/shorten` |
| **Log stream** | one sequence of events from one instance/execution | `2026/08/21/[$LATEST]a1b2c3` |
| **Log event** | one timestamped line | `{"ts":..., "message":"created abc123"}` |

```bash
awslocal logs create-log-group --log-group-name /linkstash/app
awslocal logs create-log-stream --log-group-name /linkstash/app --log-stream-name api-1
awslocal logs put-log-events --log-group-name /linkstash/app --log-stream-name api-1 \
  --log-events 'timestamp=1755763200000,message=created slug=abc123'   # ms since epoch
awslocal logs describe-log-groups --query 'logGroups[].logGroupName'
```

Verified:

```
$ awslocal logs describe-log-groups --query 'logGroups[].logGroupName'
[ "/linkstash/app" ]
$ awslocal logs filter-log-events --log-group-name /linkstash/app --filter-pattern abc123 \
    --query 'events[].message'
[ "created slug=abc123" ]
```

Reading is the part you'll do daily:

```bash
awslocal logs tail /linkstash/app --follow             # live, human-friendly
awslocal logs filter-log-events --log-group-name /linkstash/app \
  --filter-pattern '"ERROR"' --start-time 1755763200000   # search across all streams
```

`tail` for watching, `filter-log-events` for hunting. Note timestamps are
**milliseconds** since epoch — a seconds value silently puts your event in 1970 and
you'll swear the log is empty.

---

## The Lambda connection (this is the payoff)

Every Lambda writes to `/aws/lambda/<function-name>` automatically — one log stream
per execution environment, and `print()`/`logger` output plus the START/END/REPORT
lines land there for free.

**Except it isn't free: it needs permission.** Lambda writes those logs *using your
function's execution role*. No `logs:*` in that role, no logs — and nothing tells
you. The function runs fine, returns 200, and produces total silence.

That's exactly the permissions block from
[02-2](../02_iam_and_access/02_roles_and_policies_per_service.md):

```json
{ "Effect": "Allow",
  "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
  "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/shorten:*" }
```

Invoke the linkstash function from [03-4](../03_core_services/04_lambda_apigateway.md)
and read what it said:

```bash
awslocal lambda invoke --function-name shorten --payload '{"url":"https://example.com"}' out.json
awslocal logs tail /aws/lambda/shorten                  # log group appeared on its own
```

Verified:

```
2026-08-21T09:14:02 [$LATEST]7f3a START RequestId: 6c1e... Version: $LATEST
2026-08-21T09:14:02 [$LATEST]7f3a created slug=abc123
2026-08-21T09:14:02 [$LATEST]7f3a END RequestId: 6c1e...
2026-08-21T09:14:02 [$LATEST]7f3a REPORT Duration: 18.44 ms  Billed Duration: 19 ms  Memory Size: 128 MB  Max Memory Used: 42 MB
```

That `REPORT` line is your performance data: duration, billed duration, memory
actually used. Over-provisioned memory is visible right there.

The trap is asymmetric: locally the log group shows up regardless of role, because
Floci doesn't enforce IAM. In production a missing `logs:PutLogEvents` means
you debug a live incident with nothing to read. **Check the execution role has the
logs block before you ship, every time.**

---

## Metrics: numbers over time

A metric is `namespace + name + dimensions → datapoints`. AWS publishes service
metrics for you (`AWS/Lambda` `Invocations`/`Errors`/`Duration`, `AWS/SQS`
`ApproximateNumberOfMessagesVisible`); **custom metrics** are the business facts
only your app knows — links created, backups failed, cache hit rate.

```bash
awslocal cloudwatch put-metric-data --namespace linkstash \
  --metric-name LinksCreated --value 1 --unit Count

awslocal cloudwatch get-metric-statistics --namespace linkstash --metric-name LinksCreated \
  --start-time 2026-08-21T00:00:00Z --end-time 2026-08-22T00:00:00Z \
  --period 3600 --statistics Sum
```

Verified:

```json
{ "Label": "LinksCreated",
  "Datapoints": [ { "Timestamp": "2026-08-21T09:00:00Z", "Sum": 3.0, "Unit": "Count" } ] }
```

Rule of thumb: **service metrics tell you the platform is healthy; custom metrics
tell you the product is working.** "Zero errors and zero links created" is an
outage that only a custom metric catches.

---

## Alarms

An alarm watches one metric against a threshold and changes state
(`OK` / `ALARM` / `INSUFFICIENT_DATA`).

```bash
awslocal cloudwatch put-metric-alarm --alarm-name linkstash-no-links \
  --namespace linkstash --metric-name LinksCreated --statistic Sum \
  --period 300 --evaluation-periods 2 --threshold 1 \
  --comparison-operator LessThanThreshold --treat-missing-data breaching \
  --alarm-actions arn:aws:sns:us-east-1:000000000000:linkstash-alerts

awslocal cloudwatch describe-alarms --query 'MetricAlarms[].[AlarmName,StateValue]'
# → [ [ "linkstash-no-links", "INSUFFICIENT_DATA" ] ]
```

`--alarm-actions` is an **SNS topic ARN** — the same SNS from
[03-3](../03_core_services/03_sqs_sns.md). That's the whole alerting chain:
metric → alarm → SNS topic → email/Slack/PagerDuty subscribers. `--treat-missing-data
breaching` is what turns "no data at all" into a page instead of a shrug.

---

## Retention: the classic surprise bill

**Log groups never expire by default.** A chatty Lambda at debug level, left alone
for a year, is a line on the invoice that nobody can explain. Set retention when you
create the group:

```bash
awslocal logs put-retention-policy --log-group-name /aws/lambda/shorten --retention-in-days 14
awslocal logs describe-log-groups --query 'logGroups[].[logGroupName,retentionInDays]'
# → [ [ "/aws/lambda/shorten", 14 ] ]
```

Valid values are a fixed set (1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, …).
In IaC, `aws_cloudwatch_log_group` with `retention_in_days` — and declare the group
explicitly rather than letting Lambda auto-create it, or there's nothing for Tofu to
attach retention to.

---

## boto3

```python
import boto3, time

cw   = boto3.client("cloudwatch", endpoint_url="http://localhost:4566", region_name="us-east-1")
logs = boto3.client("logs",       endpoint_url="http://localhost:4566", region_name="us-east-1")

# emit a business metric from app code — cheap, one call, no batching needed at this scale
cw.put_metric_data(Namespace="linkstash",
                   MetricData=[{"MetricName": "LinksCreated", "Value": 1, "Unit": "Count"}])

# read back the last hour of a log group, across all its streams
resp = logs.filter_log_events(logGroupName="/aws/lambda/shorten",
                              startTime=int((time.time() - 3600) * 1000))   # ms!
for e in resp["events"]:
    print(e["message"].rstrip())
```

In a real Lambda you'd just use `logging` — the runtime pipes stdout/stderr to
CloudWatch for you. `filter_log_events` is for *reading* from tooling and tests.

---

## ⚠️ Fidelity caveat

Floci stores and serves log groups, streams, events and metric datapoints
well enough to test your **wiring** — that your Lambda emits, that your code reads
the right group, that IaC creates groups with retention. What is limited:

- **Alarm evaluation** — alarms are recorded and `describe-alarms` works, but state
  transitions on a real datapoint schedule (and firing `--alarm-actions` into SNS)
  should not be trusted here.
- **Metric math, anomaly detection, extended statistics, Logs Insights queries** —
  partially or not implemented.
- **IAM on logs** — not enforced, which is precisely why the missing-`logs:*` bug
  hides locally ([02-1](../02_iam_and_access/01_access_model_iam_sts.md#️-the-caveat-community-doesnt-enforce-iam)).

Author dashboards and alarms as IaC here; validate that they actually **fire and
notify** on real AWS. An alarm you never saw go `ALARM` is an untested alarm.

---

## Recap & next

- ✅ Logs nest **group → stream → event**; `tail` to watch, `filter-log-events` to
  hunt, timestamps in **milliseconds**.
- ✅ Lambda auto-writes to `/aws/lambda/<name>` **only if its execution role grants
  `logs:CreateLogStream` + `logs:PutLogEvents`** — otherwise it's silent in prod.
- ✅ `REPORT` lines give duration and max memory used — free right-sizing data.
- ✅ **Custom metrics** (`put-metric-data`) tell you the product works; AWS service
  metrics only tell you the platform is up.
- ✅ **Alarms** compare a metric to a threshold and act via **SNS** (03-3);
  `--treat-missing-data breaching` catches total silence.
- ✅ Set **retention** (`put-retention-policy --retention-in-days 14`) — the default
  is "forever," and that's a real bill.

## Exercise

Your Lambda is deployed, returns correct responses, and CloudWatch shows **no logs
at all** — not even a log group. What's the most likely cause, and what's the exact
fix?

<details>
<summary>Answer</summary>

The **execution role is missing the `logs:*` permissions**. Lambda writes logs as
your role, so without them it can't create the log group/stream or put events — and
the failure is silent: the function still runs and returns 200. (No log group at all
is the tell; a missing group means `CreateLogGroup`/`CreateLogStream` was denied
too, not just `PutLogEvents`.)

Fix — add the block to the role's permissions policy, scoped to the function's log
group rather than `*`:

```json
{ "Effect": "Allow",
  "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
  "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/shorten:*" }
```

Better still, declare `aws_cloudwatch_log_group` for `/aws/lambda/shorten` in IaC
with `retention_in_days`, and drop `logs:CreateLogGroup` from the role — the group
already exists, so the role needs only `CreateLogStream` + `PutLogEvents`.

Why Floci didn't catch it: it doesn't enforce IAM, so the logs appeared
locally regardless of the role. This class of bug is only findable on real AWS —
which is why "check the logs block" is a deploy checklist item, not a debugging step.

</details>

**→ Next: [06-5 · RDS: a real relational database](05_rds.md)**
