# 📊 Learning Tracker

Your progress across every course in this repo, as a checkable to-do. This is the counterpart to the [README](README.md) (which is the catalog) — this page is where you track what you've *done*.

> ⏱️ **On a deadline?** If you're doing the 3-month GenAI-engineer sprint, follow the **[3-Month Sprint plan](3_MONTH_GENAI_SPRINT.md)** instead — it cuts this list down to the ~29 sections that matter and schedules them week by week. Use this full tracker only for the courses that plan includes.

## How to use

- Tick a box by changing `- [ ]` to `- [x]` (edit the file, or click the checkbox on GitHub).
- **The gate is the real "done."** A section isn't complete when you've read it — it's complete when you've passed its **test task (gate)**. Tick the box then.
- Commit after each tick. Your `git log` becomes a dated record of your learning — more honest than any streak counter.
- **See your progress any time** with one command from the repo root:

  ```bash
  # overall % complete (counts only checkbox lines, ignores this example)
  awk '/^- \[x\]/{d++} /^- \[[ x]\]/{t++} END{printf "%d/%d sections done (%.0f%%)\n", d, t, 100*d/t}' LEARNING_TRACKER.md
  ```

**Status legend:** `gate` = section ends in a graded challenge · 🏁 = capstone project · ⭐ = highest-leverage for a job-ready backend/AI role.

---

## 🎯 The job-ready path (do these in order)

This is the spine toward a high-paying backend/AI engineering role. Everything else is a specialization you add on top.

> **Python foundation → production backend → the AI integration layer → prove it works → ship it.**

### 1. Python — from scratch to FastAPI ⭐
> Core Python from "what is a variable" to a tested async web API. Skip if you're already fluent — but take the capstone to prove it.

- [ ] [01 · Fundamentals](python_complete/01_fundamentals/README.md)
- [ ] [02 · Data structures](python_complete/02_data_structures/README.md)
- [ ] [03 · Functions & modules](python_complete/03_functions_and_modules/README.md)
- [ ] [04 · Object-oriented programming](python_complete/04_oop/README.md)
- [ ] [05 · Exceptions & errors ⭐](python_complete/05_exceptions_and_errors/README.md)
- [ ] [06 · Pythonic intermediate](python_complete/06_pythonic_intermediate/README.md)
- [ ] [07 · Concurrency](python_complete/07_concurrency/README.md)
- [ ] [08 · Async](python_complete/08_async/README.md)
- [ ] [09 · FastAPI](python_complete/09_fastapi/README.md)
- [ ] 🏁 [Capstone project](python_complete/99_capstone_project.md)

### 2. FastAPI — from first route to production ⭐
> The main backend course: one app (**linkbox**) grown from first route to a shipped, tested, containerized service. Every section is gated.

- [ ] [01 · Modern Python baseline](fastapi_complete/01_modern_python_async/README.md) — gate
- [ ] [02 · FastAPI fundamentals & Pydantic v2](fastapi_complete/02_fastapi_fundamentals_pydantic/README.md) — gate
- [ ] [03 · Request handling: forms, files & parsing](fastapi_complete/03_request_handling_files_parsing/README.md) — gate
- [ ] [04 · Dependency injection & app structure](fastapi_complete/04_dependency_injection_app_structure/README.md) — gate
- [ ] [05 · Async database: SQLAlchemy 2.0 + Alembic](fastapi_complete/05_async_database_sqlalchemy_alembic/README.md) — gate
- [ ] [06 · Clean architecture](fastapi_complete/06_clean_architecture/README.md) — gate
- [ ] [07 · Security & authentication](fastapi_complete/07_security_auth/README.md) — gate
- [ ] [08 · Redis: caching, rate limiting & jobs](fastapi_complete/08_redis_caching_jobs/README.md) — gate
- [ ] [09 · Testing like you mean it](fastapi_complete/09_testing/README.md) — gate
- [ ] [10 · Robustness & observability](fastapi_complete/10_robustness_observability/README.md) — gate
- [ ] [11 · Production: Docker, CI/CD & deployment](fastapi_complete/11_production_docker_cicd/README.md) — gate
- [ ] 🏁 [Capstone: DevBoard](fastapi_complete/99_capstone_devboard.md)

### 3. Build MCP Servers ⭐
> The scarce 2026 skill: build the integration layer between models and real systems. Grows one server (**notevault**) to authenticated, secured, deployed.

- [ ] [01 · Foundations](mcp_servers/01_foundations/README.md) — gate
- [ ] [02 · First server with FastMCP](mcp_servers/02_first_server_fastmcp/README.md) — gate
- [ ] [03 · Resources, prompts & Context](mcp_servers/03_resources_and_prompts/README.md) — gate
- [ ] [04 · Tools over real systems](mcp_servers/04_real_backends/README.md) — gate
- [ ] [05 · Remote & authenticated servers](mcp_servers/05_remote_and_auth/README.md) — gate
- [ ] [06 · Securing MCP servers](mcp_servers/06_security/README.md) — gate
- [ ] [07 · Test, ship & consume](mcp_servers/07_test_ship_consume/README.md) — gate
- [ ] 🏁 [Capstone: notevault](mcp_servers/99_capstone_notevault.md)

### 4. LLM Evals & Observability ⭐
> The interview differentiator: prove an AI system works — datasets, metrics, LLM-as-judge, tracing, and a CI gate that blocks regressions.

- [ ] [01 · Foundations](llm_evals_observability/01_foundations/README.md)
- [ ] [02 · Datasets](llm_evals_observability/02_datasets/README.md)
- [ ] [03 · Metrics](llm_evals_observability/03_metrics/README.md)
- [ ] [04 · LLM-as-judge](llm_evals_observability/04_llm_as_judge/README.md)
- [ ] [05 · RAG evaluation](llm_evals_observability/05_rag_evaluation/README.md)
- [ ] [06 · Tracing & observability](llm_evals_observability/06_tracing_observability/README.md)
- [ ] [07 · CI regression gates](llm_evals_observability/07_ci_regression/README.md)
- [ ] [08 · Guardrails](llm_evals_observability/08_guardrails/README.md)
- [ ] 🏁 [Project: EvalKit](llm_evals_observability/99_project_evalkit/README.md)

---

## 🤖 AI / LLM track

The agent-building depth that sits on top of the core path. Do **LangChain & RAG** first, then LangGraph, then ADK.

### LangChain & RAG
- [ ] [01 · Foundations](langchain_rag/01_foundations/README.md)
- [ ] [02 · LangChain core](langchain_rag/02_langchain_core/README.md)
- [ ] [03 · RAG fundamentals](langchain_rag/03_rag_fundamentals/README.md)
- [ ] [04 · Advanced RAG](langchain_rag/04_advanced_rag/README.md)
- [ ] [05 · Tool calling & agents](langchain_rag/05_tool_calling_and_agents/README.md)
- [ ] 🏁 [Project: document assistant](langchain_rag/99_project_doc_assistant/README.md)

### LangGraph
- [ ] [01 · Foundations](langgraph/01_foundations/README.md)
- [ ] [02 · Execution model](langgraph/02_execution_model/README.md)
- [ ] [03 · Building graphs](langgraph/03_building_graphs/README.md)
- [ ] [04 · Control flow](langgraph/04_control_flow/README.md)
- [ ] [05 · Persistence & memory](langgraph/05_persistence_and_memory/README.md)
- [ ] [06 · Human-in-the-loop](langgraph/06_human_in_the_loop/README.md)
- [ ] [07 · Multi-agent](langgraph/07_multi_agent/README.md)
- [ ] [08 · Real-world use cases](langgraph/08_real_world/README.md)
- [ ] [09 · Pitfalls & production](langgraph/09_pitfalls_and_production/README.md)
- [ ] [10 · Platform & deployment](langgraph/10_platform_and_deployment/README.md)
- [ ] 🏁 [Project: research assistant](langgraph/99_project_research_assistant/README.md)

### Google ADK
- [ ] [01 · Foundations](google_adk/01_foundations/README.md)
- [ ] [02 · Agents & workflows](google_adk/02_agents_and_workflows/README.md)
- [ ] [03 · Tools](google_adk/03_tools/README.md)
- [ ] [04 · State, sessions & memory](google_adk/04_state_sessions_memory/README.md)
- [ ] [05 · Multi-agent systems](google_adk/05_multi_agent_systems/README.md)
- [ ] [06 · Runtime, events & streaming](google_adk/06_runtime_events_streaming/README.md)
- [ ] [07 · Evaluation & quality](google_adk/07_evaluation_and_quality/README.md)
- [ ] [08 · Deployment & A2A](google_adk/08_deployment_and_a2a/README.md)
- [ ] 🏁 [Project: ADK research assistant](google_adk/99_project_adk_research_assistant/README.md)

### AI projects (pick what interests you)
- [ ] 🏁 [LangGraph Proposal Agent](langgraph_proposal_agent/README.md) — 5 sections + capstone
- [ ] 🏁 [Faceless YouTube Studio](faceless_youtube_agent/README.md) — 5 sections + capstone
- [ ] 🏁 LangGraph F&O Trading Bot — 9 lessons *(listed in the catalog; content not yet in the repo)*

---

## 🐳 Infrastructure / DevOps track

Takes the container your backend course produces all the way to a cloud deployment. Order: Docker → Kubernetes / CI-CD → OpenTofu → AWS.

### Docker
- [ ] [01 · Core concepts](docker/01_core_concepts.md)
- [ ] [02 · Dockerfile deep dive](docker/02_dockerfile_deep_dive.md)
- [ ] [03 · Networking & volumes](docker/03_networking_and_volumes.md)
- [ ] [04 · Docker Compose](docker/04_docker_compose.md)
- [ ] [05 · Security & Docker Scout](docker/05_security_and_docker_scout.md)
- [ ] [06 · CI/CD & production](docker/06_cicd_and_production.md)
- [ ] 🏁 [07 · Practical project](docker/07_practical_project.md)

### Kubernetes
- [ ] [01 · Foundations](kubernetes/01_foundations/README.md)
- [ ] [02 · Config, health & scaling](kubernetes/02_config_health_scaling/README.md)
- [ ] [03 · Deploying linkstash](kubernetes/03_deploying_linkstash/README.md)
- [ ] [04 · Production](kubernetes/04_production/README.md)
- [ ] 🏁 [Project: linkstash on k8s](kubernetes/99_project_linkstash_k8s/README.md)

### CI/CD with GitHub Actions
- [ ] [01 · Foundations](cicd_github_actions/01_foundations/README.md)
- [ ] [02 · Continuous integration](cicd_github_actions/02_continuous_integration/README.md)
- [ ] [03 · Build & artifacts](cicd_github_actions/03_build_and_artifacts/README.md)
- [ ] [04 · Delivery & deployment](cicd_github_actions/04_delivery_and_deployment/README.md)
- [ ] [05 · Advanced & shipping](cicd_github_actions/05_advanced_and_shipping/README.md)
- [ ] 🏁 [Project: CI/CD pipeline](cicd_github_actions/99_project_cicd_pipeline/README.md)

### OpenTofu / IaC
- [ ] [01 · Foundations](opentofu_iac/01_foundations/README.md)
- [ ] [02 · Core workflow](opentofu_iac/02_core_workflow/README.md)
- [ ] [03 · Modularizing](opentofu_iac/03_modularizing/README.md)
- [ ] [04 · Production](opentofu_iac/04_production/README.md)
- [ ] 🏁 [Project: Tofu linkstash](opentofu_iac/99_project_tofu_linkstash/README.md)

### AWS on LocalStack
- [ ] [01 · Foundations](aws_localstack/01_foundations/README.md)
- [ ] [02 · Core services](aws_localstack/02_core_services/README.md)
- [ ] [03 · IaC with OpenTofu](aws_localstack/03_iac_with_opentofu/README.md)
- [ ] [04 · Testing & CI](aws_localstack/04_testing_and_ci/README.md)
- [ ] [05 · More services](aws_localstack/05_more_services/README.md)
- [ ] 🏁 [Project: linkstash cloud](aws_localstack/99_project_linkstash_cloud/README.md)

---

## 🔐 Security track

- [ ] Build a Python SDK — see [Backend extras](#-backend-extras) *(prereq for tooling)*

### Ethical Hacking & Pentesting
- [ ] [01 · Networking fundamentals](ethical_hacking/01_networking_fundamentals/README.md)
- [ ] [02 · Linux for hackers](ethical_hacking/02_linux_for_hackers/README.md)
- [ ] [03 · Essential tools](ethical_hacking/03_essential_tools/README.md)
- [ ] [04 · Ethical hacking methodology](ethical_hacking/04_ethical_hacking_methodology/README.md)
- [ ] [05 · Web application security](ethical_hacking/05_web_application_security/README.md)
- [ ] [06 · CTF & career](ethical_hacking/06_ctf_and_career/README.md)
- [ ] 🏁 [Project: pentest lab](ethical_hacking/99_project_pentest_lab/README.md)

### Secure Code Audit
- [ ] [01 · Foundations](secure_code_audit/01_foundations/README.md)
- [ ] [02 · Reading code for vulns](secure_code_audit/02_reading_code_for_vulns/README.md)
- [ ] [03 · Static analysis with AST](secure_code_audit/03_static_analysis_with_ast/README.md)
- [ ] [04 · Tools & dependencies](secure_code_audit/04_tools_and_dependencies/README.md)
- [ ] [05 · LLM-assisted & shipping](secure_code_audit/05_llm_assisted_and_shipping/README.md)
- [ ] 🏁 [Project: code audit](secure_code_audit/99_project_codeaudit/README.md)

### Face Unlock on Linux
- [ ] [01 · Foundations](face_unlock_linux/01_foundations/README.md)
- [ ] [02 · Capturing & detecting](face_unlock_linux/02_capturing_and_detecting/README.md)
- [ ] [03 · Recognition & enrollment](face_unlock_linux/03_recognition_and_enrollment/README.md)
- [ ] [04 · Liveness & anti-spoofing](face_unlock_linux/04_liveness_and_antispoofing/README.md)
- [ ] [05 · PAM integration](face_unlock_linux/05_pam_integration/README.md)
- [ ] [06 · Howdy — the real tool](face_unlock_linux/06_howdy_the_real_tool/README.md)
- [ ] 🏁 [Project: face unlock](face_unlock_linux/99_project_face_unlock/README.md)

---

## 🗄️ Data & domain track

### Network Inventory
- [ ] [01 · Inventory management](network_inventory/01_inventory_management.md)
- [ ] [02 · Data models](network_inventory/02_data_models.md)
- [ ] [03 · TMF standards](network_inventory/03_tmf_standards.md)
- [ ] 🏁 [04 · Practical project](network_inventory/04_practical_project.md)

### Inventory Data Engineering
- [ ] [01 · Relational modeling](inventory_data_engineering/01_relational_modeling.md)
- [ ] [02 · API design](inventory_data_engineering/02_api_design.md)
- [ ] [03 · ETL & profiling](inventory_data_engineering/03_etl_and_profiling.md)
- [ ] [04 · Graph migration & modeling](inventory_data_engineering/04_graph_migration_and_modeling.md)
- [ ] [05 · Graph queries](inventory_data_engineering/05_graph_queries.md)
- [ ] [06 · ML & analytics](inventory_data_engineering/06_ml_and_analytics.md)
- [ ] 🏁 [07 · Practical project](inventory_data_engineering/07_practical_project.md)

---

## 🧰 Backend extras

Reinforcement and adjacent backend skills — valuable, not on the critical path.

### Building a Python SDK
> Ship a real, installable, typed library to PyPI with CI. The "I can build tooling others depend on" credential.
- [ ] [01 · Foundations](python_sdk/01_foundations/README.md)
- [ ] [02 · Packaging basics](python_sdk/02_packaging_basics/README.md)
- [ ] [03 · The sync client](python_sdk/03_the_sync_client/README.md)
- [ ] [04 · Data models](python_sdk/04_data_models/README.md)
- [ ] [05 · Robustness](python_sdk/05_robustness/README.md)
- [ ] [06 · Async client](python_sdk/06_async_client/README.md)
- [ ] [07 · Testing](python_sdk/07_testing/README.md)
- [ ] [08 · Packaging & publishing](python_sdk/08_packaging_publishing/README.md)
- [ ] [09 · Docs & developer experience](python_sdk/09_docs_and_dx/README.md)
- [ ] 🏁 [Project: pokesdk](python_sdk/99_project_pokesdk/README.md)

### FastAPI · Async · WebSockets
> Real-time + streaming AI. Do it after the main FastAPI course for the async/WebSocket depth.
- [ ] [01 · Async Python](fastapi_async_websockets/01_async_python/README.md)
- [ ] [02 · FastAPI basics](fastapi_async_websockets/02_fastapi_basics/README.md)
- [ ] [03 · WebSockets](fastapi_async_websockets/03_websockets/README.md)
- [ ] [04 · Streaming AI](fastapi_async_websockets/04_streaming_ai/README.md)
- [ ] [05 · Production-grade FastAPI](fastapi_async_websockets/05_fastapi_production/README.md)
- [ ] 🏁 [Project: streaming AI chat](fastapi_async_websockets/99_project_streaming_chat.md)

### Production FastAPI Backend (TaskFlow)
> An alternate, faster-paced take on the same production territory as the main FastAPI course. Great as a second pass / reference.
- [ ] [01 · Foundations & structure](fastapi_production_backend/01_foundations_and_structure/README.md)
- [ ] [02 · Data layer](fastapi_production_backend/02_data_layer/README.md)
- [ ] [03 · Schemas & CRUD](fastapi_production_backend/03_schemas_and_crud/README.md)
- [ ] [04 · Auth & security](fastapi_production_backend/04_auth_and_security/README.md)
- [ ] [05 · API design & robustness](fastapi_production_backend/05_api_design_and_robustness/README.md)
- [ ] [06 · Testing](fastapi_production_backend/06_testing/README.md)
- [ ] [07 · Integrations](fastapi_production_backend/07_integrations/README.md)
- [ ] [08 · Observability & ops](fastapi_production_backend/08_observability_and_ops/README.md)
- [ ] [09 · Containerization & deploy](fastapi_production_backend/09_containerization_and_deploy/README.md)
- [ ] 🏁 [Capstone: TaskFlow](fastapi_production_backend/99_project_taskflow/README.md)

### ffmpeg & Media Processing
> The media engine under any video product. Prereq for the Faceless YouTube project.
- [ ] [01 · Foundations](ffmpeg_media_processing/01_foundations/README.md)
- [ ] [02 · Core operations](ffmpeg_media_processing/02_core_operations/README.md)
- [ ] [03 · Filters](ffmpeg_media_processing/03_filters/README.md)
- [ ] [04 · Subtitles & captions](ffmpeg_media_processing/04_subtitles/README.md)
- [ ] [05 · Encoding & quality](ffmpeg_media_processing/05_encoding/README.md)
- [ ] [06 · Python automation](ffmpeg_media_processing/06_python_automation/README.md)
- [ ] 🏁 [Project: mediakit](ffmpeg_media_processing/99_project_mediakit/README.md)

---

## 🏆 Portfolio checklist

The job market rewards deployed, public repos over completed courses. Tick these as you publish them:

- [ ] **DevBoard** (FastAPI capstone) — pushed to GitHub with a working README, tests green, `docker compose up` from a clean clone
- [ ] **notevault** (MCP capstone) — deployed HTTP server, an agent consuming it, injection drill documented
- [ ] **EvalKit** eval suite wired into one of the above as a CI gate
- [ ] A short write-up per project: what it does, one architecture diagram, and an honest "what I'd do next"
- [ ] CV / LinkedIn updated with the repo links

---

*Add your own courses to a track above as the repo grows — one `- [ ]` line per section, gate noted.*
