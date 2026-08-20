# 🎯 3-Month GenAI Engineer Sprint

> **Your constraints:** ~12 hrs/week (evenings) · already know Python + basic FastAPI · target = **AI/GenAI engineer**.
> **The math:** ~12 weeks × 12 hrs ≈ **144 hours**. That's a scalpel budget. This plan cuts ~75% of the repo and keeps only what gets you *interview-ready with a portfolio*.

> ⚡ **Interview incoming — pub/sub required.** Don't wait for its slot in the schedule. Read **[08-4 · Pub/sub & cross-worker real-time](fastapi_complete/08_redis_caching_jobs/04_pubsub_realtime.md)** now (~40 min) — it's standalone. Then rehearse the talking points below. The one line that lands it: *"pub/sub broadcasts to every subscriber with no persistence; a queue delivers one message durably to one worker — notify-many-now vs get-one-job-done."*
>
> **Cloud/backend interview?** The role you got invited to leans backend + cloud (GCP, Pub/Sub, Gunicorn, Terraform). Warm up with the **[Cloud & Messaging Interview Cheat Sheet](INTERVIEW_CLOUD_CHEATSHEET.md)** — GCP-from-AWS mapping, the three-way Pub/Sub distinction, and Gunicorn/Terraform quick-answers.
>
> **Interview prep checklist:**
> - [ ] Read lesson 08-4; run the two-terminal `redis-cli` exercise (`SUBSCRIBE` / `PUBLISH`) so you've *seen* it, not just read it
> - [ ] Can explain **pub/sub vs queue** in one breath (delivery, persistence, use case)
> - [ ] Can explain **why one process can't broadcast to another's WebSocket clients**, and how Redis pub/sub fixes it (the cross-worker fan-out)
> - [ ] Can name the **at-most-once catch** and what you'd switch to for durable broadcast (**Redis Streams** / a broker)
> - [ ] Can sketch the code shape: **publish** = one-line fire-and-forget; **subscribe** = long-lived listener in **lifespan**, on a **dedicated `redis.pubsub()` connection**

## The honest frame (read this once)

144 hours makes you **interview-ready with a deployed portfolio** — not guaranteed an offer at day 90. Offers come from the portfolio *plus* applications you start in **Week 9**, not Week 12, and continue past month 3. Interviews take weeks; don't wait for "perfect" to apply.

The profile you're building — the one the 2026 market pays a premium for — is **"can turn an LLM demo into a deployed, tested, secured system."** Not "watched agent tutorials." Everything below serves that one sentence.

## Rules that keep you on track

1. **One capstone repo from Week 1.** Every phase *adds* to it. You never start fresh. By Week 12 it's a real deployed system, not a folder of tutorials.
2. **Ship > perfect.** A deployed ugly thing beats a beautiful local thing. Recruiters open the URL, not your feelings about the code.
3. **Public GitHub from day 1. Commit daily.** The commit history is proof of the grind.
4. **The gate is "done," not "I read it."** Tick a box only when you've passed the section's test task.
5. **Apply from Week 9.** In parallel with finishing. This is non-negotiable.

---

## What's IN (≈29 sections) and what's OUT

**IN — the critical path:**
- Backend spine (the parts you don't already have): DB + migrations, clean architecture, auth, Redis, testing, Docker/CI
- RAG (the LLM-app base)
- LangGraph (stateful agents — the framework that matters)
- **Build MCP Servers** (your scarcest differentiator; builds on your FastAPI)
- LLM Evals (the interview differentiator almost nobody has)

**OUT — deliberately skipped (do post-hire, not now):**
- `python_complete`, FastAPI fundamentals (you have these)
- `google_adk` (LangGraph already covers agents; ADK is a nice-to-have later)
- LangGraph 08–10 (real-world/pitfalls/platform — skim after you're hired)
- Evals: datasets-deep / guardrails (fold the essentials in)
- Kubernetes, OpenTofu, AWS, Security track, Data track, Media (none serve *this* 90-day goal)

If a specific job posting demands one of the OUT items, pull just that section in. Otherwise, stay on the path.

---

## Phase 1 · A backend you can deploy (Weeks 1–3)

**Goal:** a tested, containerized, authenticated FastAPI service — the substrate every agent runs inside. You know the basics, so we go straight to production depth.

- **Week 1** — [FastAPI 05 · Async DB (SQLAlchemy + Alembic)](fastapi_complete/05_async_database_sqlalchemy_alembic/README.md) + [06 · Clean architecture](fastapi_complete/06_clean_architecture/README.md)
  - [ ] Passed both gates · **Deliverable:** layered app on real Postgres with migrations
- **Week 2** — [FastAPI 07 · Security & auth](fastapi_complete/07_security_auth/README.md) + [09 · Testing](fastapi_complete/09_testing/README.md)
  - [ ] Passed both gates · **Deliverable:** JWT auth + a green test suite
- **Week 3** — [FastAPI 08 · Redis (cache/limits/jobs + pub/sub)](fastapi_complete/08_redis_caching_jobs/README.md) + [11 · Docker & CI/CD](fastapi_complete/11_production_docker_cicd/README.md)
  - [ ] Passed both gates, **including [08-4 · Pub/sub](fastapi_complete/08_redis_caching_jobs/04_pubsub_realtime.md)** *(pull this earlier if your interview is before Week 3)* · **Deliverable:** dockerized service, green CI pipeline
  - *(Skim [10 · Observability](fastapi_complete/10_robustness_observability/README.md) — steal just the request-ID logging.)*

**✅ Phase 1 checkpoint:** you can ship a tested, containerized, authenticated API from a clean clone.

---

## Phase 2 · RAG + the LLM-app base (Weeks 4–6)

**Goal:** "chat with your data" running behind *your own* API.

- **Week 4** — [LangChain & RAG 01 · Foundations](langchain_rag/01_foundations/README.md) + [02 · LangChain core](langchain_rag/02_langchain_core/README.md)
  - [ ] Done
- **Week 5** — [RAG 03 · RAG fundamentals](langchain_rag/03_rag_fundamentals/README.md) + [04 · Advanced RAG](langchain_rag/04_advanced_rag/README.md)
  - [ ] Done · **Deliverable:** a retrieval pipeline over real documents
- **Week 6** — [RAG 05 · Tool calling & agents](langchain_rag/05_tool_calling_and_agents/README.md) + [LLM Evals 01 · Foundations](llm_evals_observability/01_foundations/README.md)
  - [ ] Done · **Deliverable:** RAG wrapped in your FastAPI backend, one endpoint

**✅ Phase 2 checkpoint:** a grounded "chat with your docs" service you can demo behind your own auth.

---

## Phase 3 · Agents + MCP — the scarce stuff (Weeks 7–9)

**Goal:** a stateful multi-agent graph, and your **own MCP server** exposing real tools. This is the differentiator phase — go slow, go deep.

- **Week 7** — [LangGraph 01 · Foundations](langgraph/01_foundations/README.md) + [02 · Execution model](langgraph/02_execution_model/README.md) + [03 · Building graphs](langgraph/03_building_graphs/README.md)
  - [ ] Done
- **Week 8** — [LangGraph 04 · Control flow](langgraph/04_control_flow/README.md) + [05 · Persistence & memory](langgraph/05_persistence_and_memory/README.md) + [07 · Multi-agent](langgraph/07_multi_agent/README.md)
  - [ ] Done · **Deliverable:** a multi-agent graph with memory · *(skim [06 · HITL](langgraph/06_human_in_the_loop/README.md))*
- **Week 9** — [MCP 01–04](mcp_servers/README.md): [Foundations](mcp_servers/01_foundations/README.md) · [First server](mcp_servers/02_first_server_fastmcp/README.md) · [Resources & prompts](mcp_servers/03_resources_and_prompts/README.md) · [Real backends](mcp_servers/04_real_backends/README.md)
  - [ ] Passed gates · **Deliverable:** an MCP server exposing your backend as tools
  - [ ] **▶ Start applying to jobs this week.** Portfolio is demo-able now.

**✅ Phase 3 checkpoint:** a stateful agent + a real MCP server you built. This is already a stronger portfolio than most applicants.

---

## Phase 4 · Ship it + prove it (Weeks 10–12)

**Goal:** deploy the whole thing, put an eval gate on it, write it up. Keep applying.

- **Week 10** — [MCP 05 · Remote & auth](mcp_servers/05_remote_and_auth/README.md) + [06 · Security](mcp_servers/06_security/README.md) + [07 · Test/ship/consume](mcp_servers/07_test_ship_consume/README.md)
  - [ ] Passed gates · **Deliverable:** deployed, authenticated MCP server consumed by your LangGraph agent
- **Week 11** — [Evals 03 · Metrics](llm_evals_observability/03_metrics/README.md) + [04 · LLM-as-judge](llm_evals_observability/04_llm_as_judge/README.md) + [06 · Tracing](llm_evals_observability/06_tracing_observability/README.md) + [07 · CI regression](llm_evals_observability/07_ci_regression/README.md)
  - [ ] Done · **Deliverable:** an eval suite gating your agent in CI
- **Week 12** — Capstone polish, deploy, write-up
  - [ ] README + architecture diagram + **eval report** ("failure rate before/after my guardrails")
  - [ ] Deployed and reachable by a public URL
  - [ ] CV + LinkedIn updated with the repo link

**✅ Phase 4 checkpoint:** a deployed, evaluated, documented GenAI system — and a live job search.

---

## The capstone (built across all 12 weeks, not just Week 12)

**Concrete spec → [PROJECT · "askme" portfolio assistant](PROJECT_portfolio_assistant.md).** A grounded conversational assistant over a **deep knowledge base of how you executed each project**, plus personal Q&A — cited, evaluated so it won't fabricate facts about you, injection-resistant, cost-capped, streaming, deployed. It fuses RAG + agent/tools + evals + guardrails + production FastAPI, **is about you**, and ships as a live URL recruiters can talk to. Writing the project deep-dives doubles as your STAR interview prep.

It doesn't need to be big. It needs to be **real, deployed, and explainable**. In interviews you'll tell its failure stories: the stale cache, the agent that looped, the eval that caught a regression before it shipped. That's what "production experience" sounds like — and you'll have actually lived it.

Every phase feeds this one repo:
- Phase 1 → the backend + auth + Docker/CI
- Phase 2 → the RAG endpoint
- Phase 3 → the agent graph + MCP server
- Phase 4 → deploy + the eval gate + the write-up

---

## 🔀 Alternate track: the backend + cloud interview

The role you got invited to leans **backend + cloud** (GCP, Pub/Sub, Gunicorn, Terraform) more than pure GenAI. It shares Phase 1's backend spine, then diverges into cloud/infra. Run this **in parallel** for that interview — most of it you already have in the repo. Do it in this order (quick, high-frequency-asked things first):

- [ ] **Gunicorn** — [FastAPI 11-4](fastapi_complete/11_production_docker_cicd/04_gunicorn_workers.md) (~half a day). WSGI-vs-ASGI, worker sizing, Nginx.
- [ ] **Pub/Sub** — [FastAPI 08-4](fastapi_complete/08_redis_caching_jobs/04_pubsub_realtime.md) for the pattern, then the **Redis-vs-GCP distinction** in the [cloud cheat sheet](INTERVIEW_CLOUD_CHEATSHEET.md) (~1 day). GCP Pub/Sub is durable/at-least-once → consumers must be idempotent.
- [ ] **Terraform via OpenTofu** — the [OpenTofu course](opentofu_iac/) (~1 week). It *is* Terraform proficiency; say "OpenTofu, the open-source Terraform fork."
- [ ] **GCP fundamentals** — learned as "the GCP name for the AWS thing I know" ([cheat sheet](INTERVIEW_CLOUD_CHEATSHEET.md) mapping): Cloud Run, GCS, Pub/Sub, BigQuery, IAM/service accounts (~1 week).
- [ ] **The proof project** — [linkbox on GCP](PROJECT_linkbox_on_gcp.md): deploy your FastAPI app to Cloud Run with OpenTofu, Pub/Sub → BigQuery, keyless CI. Earns GCP + Terraform + Pub/Sub + Gunicorn on your resume with a live URL.

**Before the call:** rehearse the [cloud cheat sheet](INTERVIEW_CLOUD_CHEATSHEET.md)'s 60-second self-test out loud. Lead every answer with the tradeoff, then the detail.

---

## If you fall behind (you will, some weeks)

Protect the differentiators. Cut in this order:
1. First cut: skim LangGraph persistence/multi-agent to the essentials.
2. Then: trim evals to metrics + CI-gate only (drop judge/tracing depth).
3. **Never cut:** the MCP server, one deployed capstone, and the eval *gate*. Those three are the interview-winners. A smaller project that's deployed and evaluated beats a bigger one that's neither.

Track granular progress in the [Learning Tracker](LEARNING_TRACKER.md); this file is your week-by-week battle plan.

*90 days. One repo. Ship it.*
