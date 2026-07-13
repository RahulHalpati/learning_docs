# 04: Real-World Use Cases

> **Level:** Intermediate  
> **Prerequisites:** Modules 00–03  
> **Time:** 1–1.5 hours  
> **What You'll Learn:** How LangGraph solves real production problems across three domains  
> **Last Updated:** 2026-05-05

---

## Introduction

**What:** Three complete, production-relevant use cases showing LangGraph in action.  
**Why:** Knowing the API isn't enough — you need to see how concepts combine in real scenarios.  
**Focus:** Architecture decisions, not just code. Each scenario explains *why* LangGraph is the right choice over simpler alternatives.

---

## Use Case 1: Customer Support Chatbot with Escalation

**Scenario:** A SaaS company needs a chatbot that:
- Answers FAQs from a knowledge base
- Handles account-related queries using tools (check balance, update profile)
- Escalates to a human agent when it can't help
- Remembers the full conversation across sessions

**Why LangGraph (not a simple chain):**
- Needs **conditional routing** (FAQ vs account vs escalation)
- Needs **conversation memory** across turns
- Needs **human-in-the-loop** for escalation
- Needs **loops** (clarify → retry → clarify)

```python
"""
customer_support_bot.py — Production-style customer support agent
"""
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool


# ── State ──
class SupportState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str             # "faq", "account", "escalate", "resolved"
    customer_id: str        # For account lookups
    escalation_reason: str  # Why the bot couldn't help


# ── Tools ──
@tool
def check_account_balance(customer_id: str) -> str:
    """Check the account balance for a customer.

    Args:
        customer_id: The unique customer identifier
    """
    # Production: query your database
    balances = {"C001": "$1,250.00", "C002": "$89.50"}
    return f"Balance for {customer_id}: {balances.get(customer_id, 'Not found')}"


@tool
def update_customer_email(customer_id: str, new_email: str) -> str:
    """Update the email address for a customer account.

    Args:
        customer_id: The unique customer identifier
        new_email: The new email address to set
    """
    return f"Email for {customer_id} updated to {new_email}"


# ── Nodes ──
def classify_intent(state: SupportState) -> dict:
    """Classifies the customer's intent from their message."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = llm.invoke([
        SystemMessage(content=(
            "Classify the customer's intent into exactly one category:\n"
            "- 'faq' — general questions about the product\n"
            "- 'account' — account-specific actions (balance, update info)\n"
            "- 'escalate' — complaints, refunds, or issues you can't resolve\n"
            "Respond with ONLY the category name."
        )),
        *state["messages"]
    ])
    return {"intent": response.content.strip().lower()}


def handle_faq(state: SupportState) -> dict:
    """Answers general product questions."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
    response = llm.invoke([
        SystemMessage(content=(
            "You are a friendly support agent. Answer the customer's question "
            "about our product. Be concise and helpful. If you're unsure, "
            "suggest they ask for a human agent."
        )),
        *state["messages"]
    ])
    return {"messages": [response], "intent": "resolved"}


def handle_account(state: SupportState) -> dict:
    """Handles account-related queries using tools."""
    tools = [check_account_balance, update_customer_email]
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(tools)
    response = llm.invoke([
        SystemMessage(content=(
            f"You are an account specialist. Customer ID: {state.get('customer_id', 'unknown')}. "
            "Use the available tools to help with their account request."
        )),
        *state["messages"]
    ])
    return {"messages": [response], "intent": "resolved"}


def handle_escalation(state: SupportState) -> dict:
    """Pauses the graph and notifies a human agent."""
    # This interrupt pauses execution until a human responds
    human_response = interrupt({
        "type": "escalation",
        "reason": "Customer needs human assistance",
        "conversation": [m.content for m in state["messages"][-3:]],
    })
    return {
        "messages": [("assistant", f"A human agent says: {human_response}")],
        "intent": "resolved"
    }


# ── Routing ──
def route_intent(state: SupportState) -> Literal["faq", "account", "escalate"]:
    intent = state.get("intent", "faq")
    if "account" in intent:
        return "account"
    if "escalat" in intent:
        return "escalate"
    return "faq"


# ── Build ──
builder = StateGraph(SupportState)
builder.add_node("classify", classify_intent)
builder.add_node("faq", handle_faq)
builder.add_node("account", handle_account)
builder.add_node("escalate", handle_escalation)

builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route_intent, {
    "faq": "faq",
    "account": "account",
    "escalate": "escalate",
})
builder.add_edge("faq", END)
builder.add_edge("account", END)
builder.add_edge("escalate", END)

graph = builder.compile(checkpointer=MemorySaver())
```

**Architecture Diagram:**
```
Customer Message
      │
      ▼
┌──────────────┐
│   Classify    │
│   Intent      │
└──────┬───────┘
       │
   ┌───┼───────────┐
   ▼   ▼           ▼
┌─────┐ ┌────────┐ ┌──────────┐
│ FAQ │ │Account │ │Escalation│
│     │ │(tools) │ │(HITL)    │
└──┬──┘ └───┬────┘ └────┬─────┘
   │        │            │
   └────────┴────────────┘
            │
            ▼
           END
```

---

## Use Case 2: RAG Agent with Self-Correction

**Scenario:** An enterprise knowledge assistant that:
- Retrieves documents from a vector store
- Generates answers grounded in retrieved context
- **Self-evaluates** whether the answer is actually supported by the documents
- Re-retrieves with refined queries if the answer is weak

**Why LangGraph (not a simple RAG chain):**
- Needs **loops** for self-correction (retrieve → evaluate → re-retrieve)
- Needs **conditional routing** based on quality assessment
- Simple chains are "fire and forget" — no quality control

```python
"""
rag_agent.py — RAG with self-correction loop
"""
from typing import TypedDict, Annotated, Literal
import operator
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage


class RAGState(TypedDict):
    question: str                                   # User's question
    retrieved_docs: Annotated[list[str], operator.add]  # Accumulated context
    answer: str                                     # Generated answer
    quality: str                                    # "good" or "retry"
    attempt: int                                    # Loop counter (safety)


def retrieve(state: RAGState) -> dict:
    """
    What: Fetches relevant documents from vector store.
    Production: Replace with real vector DB (Pinecone, Chroma, Weaviate).
    """
    question = state["question"]

    # Simulated retrieval — production would use embeddings + vector search
    docs = [
        f"Document about {question}: LangGraph enables stateful agent workflows...",
        f"Reference for {question}: Production agents need checkpointing...",
    ]

    return {
        "retrieved_docs": docs,
        "attempt": state.get("attempt", 0) + 1
    }


def generate(state: RAGState) -> dict:
    """Generates an answer using retrieved documents as context."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    context = "\n---\n".join(state["retrieved_docs"])
    response = llm.invoke([
        SystemMessage(content=(
            "Answer the question using ONLY the provided context. "
            "If the context doesn't contain the answer, say 'I don't have enough information.'\n\n"
            f"Context:\n{context}"
        )),
        ("user", state["question"])
    ])

    return {"answer": response.content}


def evaluate(state: RAGState) -> dict:
    """
    What: Self-evaluates whether the answer is well-supported.
    Why: Catches hallucinations and weak answers before they reach users.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    response = llm.invoke([
        SystemMessage(content=(
            "Evaluate if the answer is well-supported by the context. "
            "Consider: Is it factual? Does it address the question? Is it complete?\n"
            "Respond with ONLY 'good' or 'retry'."
        )),
        ("user", f"Question: {state['question']}\nAnswer: {state['answer']}")
    ])

    return {"quality": response.content.strip().lower()}


def quality_router(state: RAGState) -> Literal["retrieve", "end"]:
    """Routes based on quality assessment and attempt count."""
    if state.get("quality") == "good" or state.get("attempt", 0) >= 3:
        return "end"
    return "retrieve"  # Loop back for more context


# Build
builder = StateGraph(RAGState)
builder.add_node("retrieve", retrieve)
builder.add_node("generate", generate)
builder.add_node("evaluate", evaluate)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", "evaluate")
builder.add_conditional_edges("evaluate", quality_router, {
    "retrieve": "retrieve",
    "end": END,
})

rag_agent = builder.compile()

# Run
result = rag_agent.invoke({
    "question": "How does LangGraph handle state persistence?",
    "retrieved_docs": [],
    "answer": "",
    "quality": "",
    "attempt": 0,
})
print(f"Answer: {result['answer']}")
print(f"Attempts: {result['attempt']}")
```

**Self-Correction Loop:**
```
Question
  │
  ▼
Retrieve ──▶ Generate ──▶ Evaluate
  ▲                          │
  │     quality="retry"      │
  └──────────────────────────┘
                             │
                   quality="good"
                             │
                             ▼
                            END
```

---

## Use Case 3: Automated Workflow Pipeline (DevOps)

**Scenario:** An automation agent that:
- Monitors log files for errors
- Classifies the severity
- Applies automatic fixes for known issues
- Creates tickets for unknown issues
- Requires human approval before applying critical fixes

**Why LangGraph:**
- **Branching** logic based on severity classification
- **Human-in-the-loop** for critical actions
- **State tracking** across the full remediation workflow

```python
"""
devops_automation.py — Automated incident response agent
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage


class IncidentState(TypedDict):
    log_entry: str          # Raw log line
    severity: str           # "low", "medium", "critical"
    diagnosis: str          # What went wrong
    action_taken: str       # What fix was applied
    ticket_id: str          # JIRA/ticket reference if created


def classify_severity(state: IncidentState) -> dict:
    """Classifies log entry severity using LLM analysis."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = llm.invoke([
        SystemMessage(content=(
            "Classify this log entry severity as: low, medium, or critical.\n"
            "- low: warnings, deprecations, non-breaking\n"
            "- medium: errors affecting some users, degraded performance\n"
            "- critical: outages, data loss, security breaches\n"
            "Respond with ONLY the severity level."
        )),
        ("user", state["log_entry"])
    ])
    return {"severity": response.content.strip().lower()}


def auto_fix(state: IncidentState) -> dict:
    """Applies automatic remediation for low/medium severity."""
    fixes = {
        "low": "Cleared warning cache, rotated log file",
        "medium": "Restarted affected service, scaled up replicas",
    }
    action = fixes.get(state["severity"], "No auto-fix available")
    return {"action_taken": action, "diagnosis": f"Auto-handled {state['severity']} issue"}


def critical_review(state: IncidentState) -> dict:
    """Pauses for human review before applying critical fixes."""
    approval = interrupt({
        "alert": "🚨 CRITICAL INCIDENT DETECTED",
        "log": state["log_entry"],
        "proposed_action": "Full service restart + page on-call engineer",
        "options": ["approve", "reject", "custom"]
    })

    if approval == "approve":
        return {
            "action_taken": "Full service restart executed (human-approved)",
            "diagnosis": "Critical incident — human-approved remediation"
        }
    return {
        "action_taken": f"Custom action: {approval}",
        "diagnosis": "Critical incident — human-directed remediation"
    }


def create_ticket(state: IncidentState) -> dict:
    """Creates a tracking ticket for the incident."""
    # Production: integrate with JIRA, Linear, etc.
    ticket = f"INC-{hash(state['log_entry']) % 10000:04d}"
    return {"ticket_id": ticket}


# Routing
def severity_router(state: IncidentState) -> Literal["auto_fix", "critical_review"]:
    if state["severity"] == "critical":
        return "critical_review"
    return "auto_fix"


# Build
builder = StateGraph(IncidentState)
builder.add_node("classify", classify_severity)
builder.add_node("auto_fix", auto_fix)
builder.add_node("critical_review", critical_review)
builder.add_node("ticket", create_ticket)

builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", severity_router, {
    "auto_fix": "auto_fix",
    "critical_review": "critical_review",
})
builder.add_edge("auto_fix", "ticket")
builder.add_edge("critical_review", "ticket")
builder.add_edge("ticket", END)

graph = builder.compile(checkpointer=MemorySaver())

# Run
config = {"configurable": {"thread_id": "incident-001"}}
result = graph.invoke(
    {
        "log_entry": "WARNING: Disk usage at 85% on worker-node-3",
        "severity": "", "diagnosis": "", "action_taken": "", "ticket_id": ""
    },
    config=config
)
print(f"Severity: {result['severity']}")
print(f"Action: {result['action_taken']}")
print(f"Ticket: {result['ticket_id']}")
```

---

## Use Case Comparison

| Aspect | Customer Support | RAG Agent | DevOps Pipeline |
|--------|-----------------|-----------|-----------------|
| **Key pattern** | Intent routing | Self-correction loop | Severity branching |
| **HITL** | Escalation | Not needed | Critical approval |
| **Memory** | Multi-turn chat | Single query | Per-incident |
| **Tools** | Account lookup | Vector search | Ticketing API |
| **Loop** | Clarification | Quality retry | None |

---

## What's Next

**Learned:** ✅ Customer support with escalation, ✅ RAG with self-correction, ✅ DevOps automation with HITL  
**Next:** Module 05: Pitfalls & Best Practices  
**Check:** Can you identify which use case pattern fits your own project?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-05 | Initial creation |
