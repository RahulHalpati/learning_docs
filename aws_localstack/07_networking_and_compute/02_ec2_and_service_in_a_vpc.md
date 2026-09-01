# 07-2 · EC2 & putting a service in a VPC

> **Level:** Intermediate · **Prerequisites:** [07-1 VPC, subnets & security groups](01_vpc_subnets_security_groups.md)
> **Time:** 25 min · **Verified:** 2026-08-21 (LocalStack 3.8.1; runs unchanged on Floci) — instances are Docker-backed; no real VM or network isolation

07-1 built the network. Now the part that makes it real: **putting something in it**. The
payoff of this lesson is small and very reusable — attaching networking to an AWS service
is always the *same two inputs*, whether the service is a virtual machine or a Lambda
function.

---

## EC2 in three nouns

| Thing | Is |
|---|---|
| **AMI** | the disk image the instance boots (`ami-…`) — OS plus whatever was baked in |
| **Instance type** | the hardware shape (`t3.micro` = 2 vCPU burstable, 1 GiB) |
| **Key pair** | the SSH keypair; AWS keeps the public half, you keep the private half |

```bash
awslocal ec2 create-key-pair --key-name linkstash --query KeyMaterial --output text > linkstash.pem

# --subnet-id  = WHERE it lives (07-1's public subnet)
# --security-group-ids = WHAT may reach it (the API tier SG)
awslocal ec2 run-instances --image-id ami-0abcdef1234567890 \
  --instance-type t3.micro --key-name linkstash \
  --subnet-id subnet-0aa11bb22 --security-group-ids sg-0abc12345
```

Those last two flags are the whole point. **`--subnet-id` + `--security-group-ids` is how
you apply networking to a service.** Everything else about EC2 is compute trivia; that pair
is the transferable knowledge.

Verified:

```
run-instances → InstanceId: i-0f1e2d3c4b5a69788
                PrivateIpAddress: 10.0.1.116   SubnetId: subnet-0aa11bb22
                State: {Code: 0, Name: pending}   OwnerId: 000000000000
```

```bash
# state and placement, without the 200-line describe dump
awslocal ec2 describe-instances --instance-ids i-0f1e2d3c4b5a69788 \
  --query 'Reservations[].Instances[].[State.Name,SubnetId,SecurityGroups[].GroupId]'
# → [["running", "subnet-0aa11bb22", ["sg-0abc12345"]]]

awslocal ec2 terminate-instances --instance-ids i-0f1e2d3c4b5a69788
# → CurrentState: shutting-down   PreviousState: running
```

That `describe-instances --query` is the honest local check: it proves your launch config
*wired the right subnet and SG*. Which is exactly — and only — what Floci can tell you.

---

## How Floci does EC2

Instances are backed by **Docker containers**, not virtual machines. `run-instances` starts
a container and gives you back a plausible `i-…` id and a private IP.

- ✅ Good for: checking that your IaC launches the **right shape** — instance count, correct
  subnet, correct SGs, correct instance profile, tags and user-data present.
- ❌ Not good for: anything kernel- or OS-level (custom AMIs, kernel modules, systemd
  specifics), **performance** or instance-type benchmarking, and — per
  [07-1's caveat](01_vpc_subnets_security_groups.md) — network reachability, since the SG
  you attached filters nothing.

A container shaped like an instance is a genuinely useful test target. Just don't read
"the instance came up and I could connect" as evidence about production.

---

## The general pattern: networking is the same two inputs everywhere

This is the part worth memorising. Wildly different services all take **subnet(s) +
security group(s)** and nothing more:

| Service | Takes | Notes |
|---|---|---|
| **EC2** | `--subnet-id`, `--security-group-ids` | the canonical case |
| **Lambda** | `VpcConfig` = `SubnetIds` + `SecurityGroupIds` | opt-in; see below |
| **RDS** | DB subnet group + VPC security groups | Floci **Pro** |
| **ElastiCache** | cache subnet group + security groups | Pro |
| **ECS / Fargate** | `awsvpcConfiguration`: subnets + security groups | Pro |
| **ALB / NLB** | subnets (≥2 AZs) + security groups | put it in the **public** subnets |

Learn the pair once and every new service's networking config is a lookup, not a lesson.

---

## Lambda in a VPC — the serverless version

By default a Lambda runs on AWS-managed networking with internet access and **no** route
into your VPC. To let it reach a private database, you give it a `VpcConfig` — the
serverless spelling of subnet + SG:

```bash
awslocal lambda update-function-configuration --function-name linkstash-api \
  --vpc-config SubnetIds=subnet-0cc33dd44,SecurityGroupIds=sg-0def67890
# same flag on create-function; subnet here is 07-1's PRIVATE subnet
```

Verified:

```
VpcConfig: {SubnetIds: ["subnet-0cc33dd44"], SecurityGroupIds: ["sg-0def67890"],
            VpcId: "vpc-1a2b3c4d"}
LastUpdateStatus: Successful
```

The function from [03-4](../03_core_services/04_lambda_apigateway.md) is now, on real AWS,
an ENI inside your subnet — so `sg-0def67890` can be the group the DB SG allows on 5432.

Two real costs to know:

1. **It loses default internet egress.** In-VPC Lambdas route like anything else in that
   subnet: no IGW route means calls to third-party APIs (or public AWS endpoints) hang
   until you add a **NAT gateway** — the one that costs real money ([07-1](01_vpc_subnets_security_groups.md)) —
   or VPC endpoints for AWS services.
2. **ENI setup on cold start.** Attaching network interfaces adds cold-start latency (much
   improved since 2019's shared-ENI rework, but not free).

So: put a Lambda in a VPC when it must reach private resources — not by default.

---

## Instance profiles: how EC2 gets AWS permissions

A Lambda gets credentials from its **execution role** ([02-2](../02_iam_and_access/02_roles_and_policies_per_service.md)).
EC2's equivalent is the same IAM role, delivered through a wrapper called an **instance
profile** — the only reason it exists is that `run-instances` needs a handle it can attach.

```bash
# the role's trust policy names ec2.amazonaws.com (vs lambda.amazonaws.com in 02-2)
awslocal iam create-role --role-name linkstash-ec2 --assume-role-policy-document \
  '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
    "Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

awslocal iam create-instance-profile --instance-profile-name linkstash-ec2
awslocal iam add-role-to-instance-profile \
  --instance-profile-name linkstash-ec2 --role-name linkstash-ec2

awslocal ec2 run-instances --image-id ami-0abcdef1234567890 --instance-type t3.micro \
  --iam-instance-profile Name=linkstash-ec2 --subnet-id subnet-0aa11bb22
```

Verified:

```
create-role             → arn:aws:iam::000000000000:role/linkstash-ec2
create-instance-profile → arn:aws:iam::000000000000:instance-profile/linkstash-ec2
run-instances           → IamInstanceProfile: {Arn: ...:instance-profile/linkstash-ec2}
```

On real AWS the SDK on that instance then picks up rotating temporary credentials from the
instance metadata service automatically — no configuration in your code.

**Never put access keys on an instance.** Not in a file, not in an env var, not baked into
an AMI. Long-lived keys don't rotate, leak through images and snapshots, and are the
classic root cause in AWS breach write-ups. Attach a role; that's what the mechanism is
for. (Attach the *permissions* policy too — the trust policy above only says who may
assume the role, it grants nothing.)

---

## When to go to real AWS

| Verify locally | Verify on real AWS |
|---|---|
| IaC creates the right VPC/subnets/SGs/instances | traffic is actually filtered as intended |
| Instances launch with the right subnet + SG + profile | private subnets are truly unreachable |
| Lambda has the intended `VpcConfig` | in-VPC Lambda egress works (NAT/endpoints) |
| IAM roles and instance profiles exist and are attached | those permissions actually grant/deny |

Everything in the left column is worth automating in CI ([05-2](../05_testing_and_ci/02_floci_in_ci.md));
nothing in the right column can be. Full fidelity list:
[05-3](../05_testing_and_ci/03_gotchas_and_pro.md).

---

## Recap & next

- ✅ `run-instances` needs an **AMI + instance type**, and networking comes from
  **`--subnet-id` + `--security-group-ids`**.
- ✅ **Same two inputs everywhere** — EC2, Lambda `VpcConfig`, RDS/ElastiCache subnet
  groups, ECS `awsvpcConfiguration`, ALB. Learn it once.
- ✅ **Lambda in a VPC** reaches private resources but **loses default internet egress**
  (needs NAT or VPC endpoints) and pays ENI cold-start cost.
- ✅ EC2 gets permissions from an **IAM role via an instance profile** — the analogue of the
  Lambda execution role. **Never** keys on an instance.
- ✅ Floci instances are **Docker containers**: good for launch-shape tests, useless
  for OS work, performance, or reachability.

## Exercise

Your linkstash Lambda must read a Postgres database that lives in a **private** subnet.
What configuration do you add — and what new problem have you just created?

<details>
<summary>Answer</summary>

**The config:** give the function a `VpcConfig` with the **private** subnet IDs (at least
two AZs for availability) and a security group of its own — then add an ingress rule on the
**DB's** security group allowing 5432 **from the Lambda's SG** (`--source-group`, the
07-1 tier pattern):

```bash
awslocal lambda update-function-configuration --function-name linkstash-api \
  --vpc-config SubnetIds=subnet-0cc33dd44,SecurityGroupIds=sg-0def67890
awslocal ec2 authorize-security-group-ingress --group-id sg-db... \
  --protocol tcp --port 5432 --source-group sg-0def67890
```

**The new problem:** the function is now on your subnet's routing, so it **loses the
default internet access** it had outside the VPC. Any outbound call — a third-party API, or
even S3/DynamoDB over their public endpoints — will hang and time out. Fixes: a **NAT
gateway** in a public subnet for general egress (real monthly cost, one per AZ for HA), or
**VPC endpoints** for the AWS services you need (cheaper, and keeps traffic off the
internet entirely). Plus the secondary cost: ENI attachment adds cold-start latency.

</details>

**→ Next: [08-1 · Bedrock for RAG & agents](../08_bedrock_and_genai/01_bedrock_for_rag_agents.md)** — or skip straight to the **[capstone](../99_project_linkstash_cloud/README.md)**.
