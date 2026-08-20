# ☁️ Cloud & Messaging Interview Cheat Sheet

Talking points for a backend + cloud interview (GCP · Pub/Sub · Gunicorn · Terraform), written for someone who **already knows AWS deeply**. This is a rehearse-before-the-call reference, not a tutorial — depth links point into the courses.

> **How to use it:** read the one-liner answers out loud until they're yours. In the room, **lead with the distinction/tradeoff**, then the detail — that's what reads as "has actually done it."

---

## 1 · GCP, in the AWS you already know

You don't need to relearn cloud — you need the GCP *name* for the AWS thing you already use, plus a few structural differences.

| Concept | AWS | **GCP** | One-line framing |
|---|---|---|---|
| VMs | EC2 | **Compute Engine** | same idea |
| Serverless containers | Fargate / App Runner | **Cloud Run** | "containerized service, request-autoscaled, scale-to-zero" |
| Serverless functions | Lambda | **Cloud Functions** | event-driven; Cloud Run for anything container-shaped |
| Object storage | S3 | **Cloud Storage (GCS)** | near-identical; buckets, storage classes |
| Managed SQL | RDS | **Cloud SQL** | Postgres/MySQL managed |
| NoSQL | DynamoDB | **Firestore** / **Bigtable** | Firestore=document, Bigtable=wide-column |
| Data warehouse | Redshift / Athena | **BigQuery** | serverless SQL, storage/compute split, pay-per-bytes-scanned |
| Messaging | SNS + SQS | **Pub/Sub** | one service = topic + durable subscriptions (see §2) |
| In-memory cache | ElastiCache | **Memorystore** | managed Redis/Memcached |
| Kubernetes | EKS | **GKE** | GKE is the reference k8s |
| Container registry | ECR | **Artifact Registry** | (was Container Registry / GCR) |
| Secrets | Secrets Manager | **Secret Manager** | same job |
| Monitoring/logs | CloudWatch | **Cloud Monitoring + Cloud Logging** | (formerly Stackdriver) |
| IaC (native) | CloudFormation | **Deployment Manager** | but everyone uses **Terraform/OpenTofu** |
| Load balancer | ALB/ELB | **Cloud Load Balancing** | GCP's is global by default |
| CLI | `aws` | **`gcloud`** (+ `gsutil`/`gcloud storage`, `bq`) | |

**The structural differences that trip up AWS people — mention one unprompted and you sound experienced:**

- **Resource hierarchy.** Everything lives in a **Project** (Organization → Folder → Project → resources). Billing, quotas, and IAM attach at the project level. There's no direct "AWS account per env" — you use **one project per environment** instead.
- **VPC is global.** A GCP VPC spans all regions; **subnets are regional**. (AWS VPCs are regional.) So a single VPC can hold resources in multiple regions.
- **IAM = roles bound to members on resources, inherited down the hierarchy.** **Service accounts are first-class workload identities** — your Cloud Run service runs *as* a service account, and you grant *that* account the roles it needs (least privilege). This is the GCP answer to "how does my app get permissions."
- **Cloud Run concurrency** is a real interview nuance: one container instance handles **multiple concurrent requests** (you set `--concurrency`), and Cloud Run scales *instances* by load. Ties directly to Gunicorn (§3): on Cloud Run you often run **one modest process** and let the platform scale instances, rather than packing many workers per container.

---

## 2 · Pub/Sub — three things that share a name ⚠️

This is the trap. "Pub/sub" in an AWS/GCP JD almost never means Redis pub/sub. Know all three and the differences cold.

| | **Redis pub/sub** | **GCP Pub/Sub** | **AWS SNS + SQS** |
|---|---|---|---|
| Durability | **none** | **durable** (retains unacked, default 7 days) | durable (SQS holds messages) |
| Delivery | **at-most-once** | **at-least-once** (exactly-once opt-in on pull) | at-least-once |
| Offline consumer | misses the message forever | gets it on reconnect | SQS holds it |
| Shape | fire-and-forget broadcast | topic → durable **subscriptions**, **push or pull** | SNS topic → fans out to SQS queues |
| Consumer must be | — | **idempotent** (dedupe on `messageId`) | **idempotent** |
| Use for | live chat, dashboards, cache signals | decoupled services, event pipelines | same, on AWS |

**The single most important point:** GCP Pub/Sub is **durable and at-least-once**, so **consumers must be idempotent** — a message can be delivered more than once (redelivery after a missed ack), so you dedupe on `messageId` or design the handler to be safe to run twice. That one sentence is what an interviewer listens for.

**Mental model:** *GCP Pub/Sub ≈ AWS SNS **and** SQS combined* — the topic fans out (SNS), and each subscription is its own durable buffer (SQS). Each subscription gets its **own copy** of every message (fan-out to independent consumers).

**Vocabulary to have ready:** topic, subscription (**push** = Pub/Sub POSTs to your endpoint; **pull** = your worker fetches), **ack deadline** (ack in time or it's redelivered), **dead-letter topic** (park poison messages after N delivery attempts), **ordering keys** (ordered delivery within a key), **exactly-once** (opt-in, pull subscriptions).

**If they push on "why not just Redis pub/sub?"**
> "Redis pub/sub is at-most-once with no persistence — fine for ephemeral fan-out like live dashboards. If a consumer is down when I publish, that message is gone. For anything that must not be lost I use a durable broker — GCP Pub/Sub, SNS+SQS, or Redis **Streams** — which retain and redeliver until acknowledged."

Pattern depth (Redis pub/sub, with the queue contrast): **[FastAPI 08-4 · Pub/sub & cross-worker real-time](fastapi_complete/08_redis_caching_jobs/04_pubsub_realtime.md)**.

---

## 3 · Gunicorn — the four things a JD tests

Full lesson: **[FastAPI 11-4 · Gunicorn](fastapi_complete/11_production_docker_cicd/04_gunicorn_workers.md)**. The quick answers:

- **"Why can't Gunicorn just run FastAPI?"** → *Gunicorn is a **WSGI** (sync) server; FastAPI is **ASGI** (async). You run Gunicorn as a process manager for **Uvicorn workers**: `gunicorn app.main:app -k uvicorn.workers.UvicornWorker`. Gunicorn supervises the processes; each Uvicorn worker runs the async event loop.*
- **Worker count.** Sync workers: `(2 × cores) + 1`. **Async (Uvicorn) workers: far fewer — ~1 per core** — because each already handles many concurrent connections; oversubscribing just wastes memory.
- **Why Gunicorn over `uvicorn --workers`?** Battle-tested master/worker supervision: crashed-worker auto-restart, **graceful reload on `SIGHUP`** (zero downtime), `--max-requests`/`--max-requests-jitter` to recycle workers and bound memory leaks.
- **Nginx in front.** Reverse proxy: terminates **TLS**, serves **static**, **buffers** slow clients (slowloris protection), sets `X-Forwarded-For`/`-Proto`. Gunicorn binds a local socket; Nginx is public.
- **Cloud-native caveat:** on **Cloud Run / k8s** you often run **one process per container and scale by replicas/instances** — Gunicorn's multi-worker supervision matters most on a **single VM/host**.

---

## 4 · Terraform / OpenTofu — you already have this

You've worked in **[OpenTofu](opentofu_iac/)** — the open-source fork of Terraform (forked from Terraform 1.5, now under the Linux Foundation, MPL-licensed). **Same HCL, same state, same modules, same `init/plan/apply`.** Say so:

> "I've used OpenTofu, the open-source Terraform fork — identical HCL and workflow. `terraform` and `tofu` are drop-in for the same configs."

Quick answers:
- **What is IaC / why?** → declarative, **idempotent**, version-controlled infra; `plan` shows the diff before `apply`; reproducible across envs; code-reviewed changes instead of console clicking.
- **State.** → `terraform.tfstate` maps config to real resources. Use a **remote backend** (GCS/S3) with **locking** so two people can't `apply` concurrently and corrupt it. Never commit state (it holds secrets).
- **Structure.** → providers, resources, data sources, **variables/outputs**, **modules** for reuse, `for_each`/`count`, remote backend. One config per environment (or workspaces).
- **The workflow.** → `init` (providers/backend) → `plan` (review diff) → `apply` → `destroy`. Plan-before-apply is the safety rail.

---

## The 60-second self-test (rehearse these)

- [ ] Name the GCP equivalent of: Lambda, S3, DynamoDB, Redshift, SNS/SQS, ElastiCache, ECR. *(Cloud Run/Functions, GCS, Firestore, BigQuery, Pub/Sub, Memorystore, Artifact Registry)*
- [ ] Why must a GCP Pub/Sub consumer be **idempotent**? *(at-least-once → possible redelivery; dedupe on `messageId`)*
- [ ] Redis pub/sub vs a durable broker — when each, and what breaks? *(at-most-once/ephemeral vs durable/redelivered; offline consumer loses the message under Redis pub/sub)*
- [ ] Why `-k uvicorn.workers.UvicornWorker`, and how many workers for async? *(WSGI manager running ASGI workers; ~1/core)*
- [ ] How do you keep Terraform state safe for a team? *(remote backend + locking; never commit it)*
- [ ] How does your Cloud Run service get permission to publish to Pub/Sub? *(it runs as a **service account**; grant that account the publisher role — least privilege)*

---

*Depth lives in the courses; this page is the pre-call warmup. Tie every answer back to something you've actually built — that's what turns a checklist into a hire.*
