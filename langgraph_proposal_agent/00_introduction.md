# 00 · Introduction

> **Level:** Beginner-friendly · **Prerequisites:** Python basics, optional LangChain exposure
> **Time:** 10 min · **Verified:** LangGraph 1.1.10, Python 3.10

---

## The proposal bottleneck

You found a good job posting. It's a FastAPI + Postgres backend — exactly your stack.
But writing the proposal takes 20 minutes: re-read the job, pick the right portfolio
project, personalise the opener, avoid sounding generic, proofread. By the time you're
done three competitors have already applied.

**What if you could paste the job and get a ready-to-send proposal in 10 seconds?**

That's what this course builds.

---

## What the finished app does

```
$ python -m proposal_agent.cli data/sample_jobs/fastapi_backend.txt

============================================================
PATH     : analyzer -> matcher -> writer -> reviewer
REVISIONS: 1
APPROVED : True
============================================================
Hi — I build exactly this. I recently shipped a typed Python/FastAPI inventory API
for a logistics startup. Clean structure, Postgres with Alembic migrations, Docker
Compose for local dev, 80%+ test coverage with pytest + TestClient.

For your project I'd suggest: FastAPI + SQLModel (or SQLAlchemy 2.x), Alembic,
Postgres in Docker, Pydantic v2 for validation, and pytest from day one.

Timeline: I can deliver an MVP (products + stock endpoints, Dockerized, tested) in
10 days, with orders + full docs in week 2. Happy to share the GitHub repo from
the logistics project so you can see the code style before committing.

Rate: $1,800 all-in (your budget range). Ready to start Monday.
— Meet
```

Four agents ran, the reviewer asked for one revision, the second draft was approved —
all in a few seconds.

---

## What you will learn

By the end of this course you can:

- Design a **multi-agent state machine** in LangGraph with a conditional revision loop
- Write **focused, testable agent functions** — each does one job well
- Build a **provider-agnostic LLM layer** (Ollama / Claude / OpenAI / fake — one env var)
- Test every agent **offline** with `GenericFakeChatModel` — no API key needed
- Serve the agent as a **FastAPI endpoint** and a **Streamlit web UI**
- **Personalise** the agent with your own `profile.yaml`

---

## How the course is structured

The course follows a **build-first** approach:

1. **Foundations** — understand the problem and the tools
2. **Building the agents** — one agent at a time, each verified
3. **Assembling the graph** — wire agents together, add the review loop
4. **Serving & frontends** — CLI → FastAPI → Streamlit
5. **Quality & shipping** — better prompts, evaluation, deployment

Every code block in this course was **actually run** and the real output is shown.
No fabricated examples.

The full working app lives in `99_project_proposal_agent/` — read it any time as a
reference, or jump straight there if you want to run first and learn second.

---

## Before you start

You need:

- Python 3.10+
- (Optional, for a real LLM) [Ollama](https://ollama.com) with any model pulled
- (Optional) Anthropic or OpenAI API key

Everything else — including running all tests — works **completely offline** with no
API keys using the built-in fake model.

**Ready? → [01 Foundations: Problem & architecture](01_foundations/01_problem_and_architecture.md)**
