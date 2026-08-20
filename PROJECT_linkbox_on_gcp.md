# 🚀 Project · linkbox on GCP — ship a FastAPI service to the cloud, as code

> **Level:** Intermediate → Advanced · **Prerequisites:** the [FastAPI course](fastapi_complete/) through Docker (you have a containerized **linkbox**), the [OpenTofu/IaC course](opentofu_iac/), and the [Cloud & Messaging cheat sheet](INTERVIEW_CLOUD_CHEATSHEET.md).
> **Time:** ~15–25 h · **Format:** specification only — you build it. This is the project that lets you put **GCP · Terraform · Pub/Sub · Cloud Run · Gunicorn · BigQuery** on your resume with a **live URL to prove it**.

Take the **linkbox** service you already built and deploy it to Google Cloud — every piece of infrastructure defined as code, nothing clicked in the console. One weekend-sized project that honestly earns the whole backend-cloud JD, reusing ~80% of what you've written.

> ⚠️ **Cost & safety — read first.** Use the GCP **$300 free-trial credit**. Cloud SQL and any `min-instances > 0` cost money while running. Keep Cloud Run at **scale-to-zero** (`min-instances = 0`), use the **smallest Cloud SQL tier**, set a **budget alert** on day one, and run **`tofu destroy`** whenever you stop working. Treating teardown as part of the workflow *is* a cloud-cost-awareness signal interviewers like.

---

## The architecture

```mermaid
flowchart LR
    U[User] -->|GET /{slug}| CR[Cloud Run: linkbox API<br/>Gunicorn + Uvicorn workers]
    CR -->|redirect| U
    CR -->|SQL| SQL[(Cloud SQL<br/>Postgres)]
    CR -->|publish click event| PS[Pub/Sub topic: clicks]
    PS -->|push subscription, OIDC| W[Cloud Run: worker]
    W -->|idempotent insert| BQ[(BigQuery<br/>click_events)]
    GH[GitHub Actions] -.->|WIF, keyless| GCP[(provision via OpenTofu)]
    GCP -.-> CR & SQL & PS & W & BQ
```

Everything in that diagram — the two Cloud Run services, Cloud SQL, the Pub/Sub topic + subscription, the BigQuery dataset, service accounts, IAM, and the Artifact Registry repo — is created by **OpenTofu/Terraform**, with **remote state in a GCS backend**.

---

## What you'll prove (the resume lines this earns)

- "Deployed a containerized **FastAPI** service to **Cloud Run** (Gunicorn + Uvicorn workers), backed by **Cloud SQL**."
- "Built an event pipeline: click events to **Pub/Sub**, consumed **idempotently** by a worker, streamed into **BigQuery** for analytics."
- "Provisioned all infrastructure with **Terraform/OpenTofu** (remote GCS state + locking, least-privilege **service accounts**)."
- "**Keyless CI/CD** from GitHub Actions to GCP via **Workload Identity Federation** — no service-account JSON keys."

Each is a true sentence backed by a public repo and a running URL. That's the difference between "familiar with GCP" and "deployed on GCP."

---

## Required components

| Component | GCP service | What it exercises (interview-relevant) |
|---|---|---|
| linkbox API | **Cloud Run** | containers, Gunicorn worker sizing, Cloud Run concurrency, scale-to-zero |
| Database | **Cloud SQL (Postgres)** | managed SQL, connecting Cloud Run → Cloud SQL, secrets |
| Click events | **Pub/Sub** (topic + subscription) | durable at-least-once messaging, push vs pull, **idempotency** |
| Consumer | **Cloud Run** (worker, push subscription) | OIDC-authenticated push, idempotent handler |
| Analytics | **BigQuery** | serverless warehouse, streaming inserts, aggregation SQL |
| Image registry | **Artifact Registry** | where the built image lives |
| All infra | **OpenTofu/Terraform** | IaC, remote state + locking, modules, least-privilege IAM |
| Deploy | **GitHub Actions + Workload Identity Federation** | keyless CI/CD to GCP |
| Secrets | **Secret Manager** | DB password / config, injected into Cloud Run |

---

## Non-negotiables

- **IaC everything.** If it exists in GCP and you made it by clicking, it doesn't count. `tofu destroy` then `tofu apply` must rebuild the whole stack.
- **Remote state.** OpenTofu state in a **GCS backend** with locking — never local, never committed (it holds secrets).
- **Least-privilege service accounts.** The API's SA can publish to the topic and read its DB secret — nothing more. The worker's SA can write to BigQuery — nothing more. No default/over-broad SAs.
- **Keyless CI.** GitHub → GCP via **Workload Identity Federation**. No `GOOGLE_CREDENTIALS` JSON key in a secret.
- **The consumer is idempotent.** Pub/Sub is at-least-once; a redelivered click event must **not** double-count. Dedupe on the Pub/Sub `messageId` (e.g. BigQuery `insertId`, or a seen-set). This is *the* point the pipeline exists to demonstrate.
- **Scale-to-zero + budget alert.** Prove you thought about cost.

---

## Milestones

| # | Milestone | Acceptance criteria |
|---|-----------|---------------------|
| **M0** | Container for Cloud Run | linkbox image runs **Gunicorn + `uvicorn.workers.UvicornWorker`**, respects the `PORT` env var Cloud Run injects, `/healthz` green locally; pushed to **Artifact Registry** |
| **M1** | Deploy via OpenTofu | `tofu apply` from a clean state provisions Cloud Run + Cloud SQL + SA/IAM + Artifact Registry, **state in GCS with locking**; the public HTTPS URL serves linkbox against Cloud SQL (migrations applied) |
| **M2** | Publish events | the redirect path publishes a click event (`{slug, ts}`) to the **Pub/Sub** topic using the API's service account; verify with `gcloud pubsub subscriptions pull` |
| **M3** | Consume → BigQuery | a **worker Cloud Run** service on a **push subscription** consumes events **idempotently** and inserts into BigQuery; clicking a link N times yields exactly N rows (prove no dupes on redelivery); an aggregation query returns top links |
| **M4** | Keyless CI/CD | GitHub Actions builds + pushes the image and runs `tofu plan` on PR / `apply` on main, authenticating via **Workload Identity Federation** (no JSON key in the repo) |
| **M5** | Harden + document | secrets in **Secret Manager**, tuned concurrency/min-instances, **budget alert**, README with the architecture diagram and a working **`tofu destroy`** teardown |

Do them in order; each is a demoable checkpoint. Stop at M3 and you already have a strong story — M4–M5 are what make it senior.

---

## Grading rubric (self-assess)

| Dimension | Strong looks like |
|-----------|-------------------|
| IaC discipline | Whole stack rebuilds from `tofu apply`; nothing clicked; state remote + locked |
| Security | Least-privilege SAs; keyless CI; secrets in Secret Manager; no keys in git |
| Messaging | Durable Pub/Sub; consumer provably idempotent under redelivery |
| Cloud fluency | Cloud Run concurrency/worker sizing reasoned; scale-to-zero; cost controlled |
| Operability | One-command deploy; teardown works; README a stranger can follow |

---

## Stretch goals (each is an interview story)

- **Private IP** Cloud SQL via a **VPC connector** instead of the public connector.
- **Dead-letter topic** on the subscription + an **exactly-once** pull subscription variant — compare the two delivery models.
- **Multi-environment** (dev/prod) via OpenTofu **workspaces** or a module + tfvars per env.
- **Cloud Monitoring** dashboard + an alert on worker errors or Pub/Sub backlog.
- **GCS + Cloud CDN** for any static assets; signed URLs for downloads.

---

## The interview stories this hands you

When they ask "tell me about something you deployed":

> "I shipped a FastAPI URL shortener to **Cloud Run** — Gunicorn managing Uvicorn workers, scale-to-zero, backed by **Cloud SQL**. Click events flow through **Pub/Sub** to a worker that writes to **BigQuery**; because Pub/Sub is at-least-once I made the consumer **idempotent** so redelivered events don't double-count. All of it is **OpenTofu** with remote GCS state, deployed by GitHub Actions using **Workload Identity Federation** so there are no long-lived keys. Everything's least-privilege service accounts, and I keep a budget alert plus a `tofu destroy` so it costs nothing idle."

That paragraph, backed by a repo and a URL, answers GCP, Terraform, Pub/Sub, Cloud Run, Gunicorn, CI/CD, and cost-awareness in one breath.

*Build it once. Tell it in every interview.*
