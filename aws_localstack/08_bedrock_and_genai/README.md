# 08 · Bedrock & GenAI on AWS

Every service so far has been storage, messaging, or compute. This module is the
one that connects this course to the [LangChain/RAG](../../langchain_rag/) and
[LangGraph](../../langgraph/) courses: **Amazon Bedrock**, AWS's managed way to
call foundation models — and the reason "AWS + GenAI" is its own line on a lot of
job descriptions right now.

| # | Module | You'll be able to… |
|---|---|---|
| 08-1 | [Bedrock for RAG & agents](01_bedrock_for_rag_agents.md) | Call Bedrock from boto3 and from LangChain, wire the IAM permissions it needs, and decide Knowledge Bases/Agents vs. your own RAG stack |

**Honest note before you start:** Bedrock needs **real AWS** — Floci's
`bedrock-runtime` is a documented **stub** (canned responses, no actual model),
so nothing here runs against the emulator. The IAM/wiring code is still worth
writing and reading; running it for real costs cents (Claude Haiku / Nova Lite
are fractions of a cent per call).

**Next → [08-1 · Bedrock for RAG & agents](01_bedrock_for_rag_agents.md)**
