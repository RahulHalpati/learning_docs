# 🏃 3-Month GenAI Sprint — Sep → Nov 2026, job switch in Jan 2027

The single track to follow. Ignore the full [catalog](README.md) until this is done — everything here was chosen against **what job postings actually screen for in 2026**, not against what's in the repo.

## 📈 Why this order (market snapshot, Aug 2026)

- **AI engineer is the #1 fastest-growing role** (postings +143% YoY, ~3:1 demand-to-candidate gap). Backend-only roles are stable but deprioritized — the market has bifurcated toward AI-integration engineers.
- **LangChain is the #1 hiring keyword** — appears in ~34% of agentic-AI listings. **RAG is the dominant enterprise pattern**: a CV without vector DBs, chunking, embeddings, and reranking is invisible.
- **LangGraph is the leading production-agent framework** in listings.
- **"Eval literacy" is the top screening differentiator** — golden datasets, LLM-as-judge, regression gates. It separates demo-builders from production engineers.
- **MCP integration** is an explicit screen in 2026 postings and still scarce among candidates.
- Median AI-engineer hire has ~3.7 yrs experience — your Python/FastAPI background + this track is exactly the profile.

**What this means:** your Python + FastAPI is already the foundation employers assume. The gap between you and the role is the AI layer, in this order: **RAG → agents → evals → MCP**.

## 🗓️ The schedule (~12 hrs/week, 13 weeks)

**The gate is "done."** A week isn't finished when you've read it — it's finished when the section's test task passes.

### Phase 1 — RAG (Weeks 1–4) · the #1 keyword
- [ ] W1 [LangChain foundations](langchain_rag/01_foundations/README.md) + [LangChain core](langchain_rag/02_langchain_core/README.md)
- [ ] W2 [RAG fundamentals](langchain_rag/03_rag_fundamentals/README.md)
- [ ] W3 [Advanced RAG](langchain_rag/04_advanced_rag/README.md) + [Tool calling & agents](langchain_rag/05_tool_calling_and_agents/README.md)
- [ ] W4 🏁 [Document assistant project](langchain_rag/99_project_doc_assistant/README.md) — **serve it behind FastAPI** (your existing skill, now with an AI layer) → **portfolio piece #1**

### Phase 2 — Agents (Weeks 5–8) · the production framework
- [ ] W5 [LangGraph foundations](langgraph/01_foundations/README.md) + [Execution model](langgraph/02_execution_model/README.md)
- [ ] W6 [Building graphs](langgraph/03_building_graphs/README.md) + [Control flow](langgraph/04_control_flow/README.md)
- [ ] W7 [Persistence & memory](langgraph/05_persistence_and_memory/README.md) + [Human-in-the-loop](langgraph/06_human_in_the_loop/README.md)
- [ ] W8 [Multi-agent](langgraph/07_multi_agent/README.md) + [Pitfalls & production](langgraph/09_pitfalls_and_production/README.md), then 🏁 [Research assistant capstone](langgraph/99_project_research_assistant/README.md) → **portfolio piece #2**

### Phase 3 — Evals (Weeks 9–10) · the interview differentiator
- [ ] W9 [Foundations](llm_evals_observability/01_foundations/README.md) + [Datasets](llm_evals_observability/02_datasets/README.md) + [Metrics](llm_evals_observability/03_metrics/README.md)
- [ ] W10 [LLM-as-judge](llm_evals_observability/04_llm_as_judge/README.md) + [RAG evaluation](llm_evals_observability/05_rag_evaluation/README.md) + [CI regression gates](llm_evals_observability/07_ci_regression/README.md) — **wire an eval CI gate into the Phase 1 doc assistant** → **portfolio piece #3**
- 📣 **Start applying now** (see timeline below). Don't wait for Phase 4.

### Phase 4 — MCP (Weeks 11–12) · the scarce skill
- [ ] W11 [Foundations](mcp_servers/01_foundations/README.md) + [First server with FastMCP](mcp_servers/02_first_server_fastmcp/README.md) + [Tools over real systems](mcp_servers/04_real_backends/README.md)
- [ ] W12 [Remote & auth](mcp_servers/05_remote_and_auth/README.md) + [Security](mcp_servers/06_security/README.md) + [Test, ship & consume](mcp_servers/07_test_ship_consume/README.md), then 🏁 [notevault capstone](mcp_servers/99_capstone_notevault.md) (trim to: deployed + one agent consuming it) → **portfolio piece #4**

### Week 13 — Buffer & polish
- [ ] Catch up on any slipped gate (something *will* slip — this week is why the plan survives)
- [ ] READMEs on all 4 portfolio repos: what it does, one diagram, honest "what I'd do next"
- [ ] CV + LinkedIn with the exact keywords: *LangChain, RAG, LangGraph, agents, LLM evals, LLM-as-judge, MCP, FastAPI, vector databases, reranking*
- [ ] Drill the [interview question bank](INTERVIEW_QUESTIONS.md)

## 📆 Application timeline (work backwards from January)

Hiring cycles run 4–8 weeks. A January start means:

| When | Do |
|------|----|
| **Early Nov** (start of W10) | First applications out — 3 portfolio pieces is enough to apply. Log everything in the [Job Tracker](JOB_TRACKER.md). |
| **Nov–Dec** | Interviews while finishing Phase 4. MCP talking points land mid-interview-loop — that's fine, it reads as "currently shipping". |
| **Dec** | Offers, notice period. |
| **Jan 2027** | Switch. |

## ✂️ What's deliberately cut (don't reopen these until hired)

- **Python & FastAPI courses** — you already have these skills; the doc assistant *is* your FastAPI proof.
- **Google ADK** — LangChain/LangGraph own the hiring volume; ADK is a post-hire specialization.
- **Docker/K8s/CI-CD/AWS/OpenTofu tracks** — you need `docker compose up` and one GitHub Actions workflow, and the eval-CI section (W10) teaches exactly that slice.
- **Security, Snowflake, data, media tracks** — zero overlap with the GenAI screening checklist.

Feeling behind? Cut LangGraph 09 and the MCP capstone polish. Never cut a gate or a portfolio README — **deployed repos beat completed sections.**
