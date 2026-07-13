# 00: Introduction to LangGraph

> **Learning Level:** Absolute Beginner  
> **Prerequisites:** Basic Python, familiarity with LLMs (helpful but not required)  
> **Time:** 20–30 minutes  
> **What You'll Learn:** What LangGraph is, why it exists, where it fits in AI architectures, and how to set up your environment  
> **Last Updated:** 2026-05-05

---

## Welcome! 👋

This is the beginning of your journey into **LangGraph** — the framework that turns LLMs from simple question-answering machines into **reliable, stateful AI agents** that can reason, loop, use tools, and coordinate with humans.

Don't worry if you're completely new — this guide assumes no prior knowledge of LangGraph and will explain everything step by step.

---

## 📌 What is LangGraph?

**In Simple Terms:**  
LangGraph is a Python framework that lets you build AI workflows as **graphs** — where each step (node) does something specific, and the connections (edges) decide what happens next. Think of it as a flowchart that an AI follows.

**Real-World Analogy:**  
Imagine a **hospital emergency room**:
- A **triage nurse** (first node) evaluates you
- Based on severity, you're **routed** (conditional edge) to a specialist or general care
- The doctor might **loop back** to run more tests (cycle in the graph)
- A pharmacist **picks up** where the doctor left off (state passing between nodes)
- At any point, a **human supervisor** can intervene (human-in-the-loop)

LangGraph lets you build AI systems that work exactly like this — with branching, looping, state management, and human oversight.

**Why It Matters:**
- **Career:** LangGraph is the industry standard for production AI agents (used by companies like Elastic, Rakuten, Replit)
- **Practical:** Build chatbots, automation pipelines, RAG systems, and multi-agent architectures
- **Skills:** Master stateful AI orchestration — the #1 gap between prototype and production AI

---

## 🧠 Where Does LangGraph Fit?

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────────┐    ┌──────────────────────────────┐  │
│   │  LangChain   │    │         LangGraph             │  │
│   │  (Ingredients)│    │  (The Recipe / Orchestrator)  │  │
│   │              │    │                              │  │
│   │  • LLM calls │───▶│  • StateGraph (workflow)     │  │
│   │  • Tools     │    │  • Nodes (actions)           │  │
│   │  • Retrievers│    │  • Edges (routing)           │  │
│   │  • Prompts   │    │  • Checkpointers (memory)    │  │
│   │  • Loaders   │    │  • Human-in-the-loop         │  │
│   └─────────────┘    └──────────────────────────────┘  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│   LLM Provider (OpenAI / Ollama / Anthropic / etc.)     │
└─────────────────────────────────────────────────────────┘
```

### The Key Distinction

| Framework | Purpose | Best For |
|-----------|---------|----------|
| **LangChain** | Individual AI components (tools, models, retrievers) | Linear RAG, simple chatbots, rapid prototyping |
| **LangGraph** | Orchestration of those components into stateful workflows | Complex agents, loops, multi-step reasoning, production systems |

**Mental Model:** LangChain gives you LEGO bricks. LangGraph is the instruction manual that tells you how to assemble them into something complex and reliable.

---

## Module Overview

| Module | Topic | What You'll Learn |
|--------|-------|-------------------|
| **00** | Introduction (this file) | What LangGraph is, setup, ecosystem |
| **01** | Core Concepts | State, Nodes, Edges, Graph lifecycle |
| **02** | Architecture & Internals | How StateGraph works under the hood |
| **03** | Practical Implementation | Minimal → Advanced code examples |
| **04** | Real-World Use Cases | Chatbot, RAG agent, automation pipeline |
| **05** | Pitfalls & Best Practices | Common mistakes, performance, scaling |
| **06** | Connections & Ecosystem | How LangGraph relates to agents, RAG, memory |
| **07** | Mini Project | Build a complete Research Assistant agent |

---

## Prerequisites and Setup

### What You Need

1. **Python 3.11+** — LangGraph requires modern Python for type hints and async support
2. **An LLM API Key** — OpenAI recommended for learning (or Ollama for local/free)
3. **A code editor** — VS Code, PyCharm, or any editor you prefer

### Installation Guide

#### Step 1: Create a Virtual Environment
```bash
# Create isolated environment — keeps your system Python clean
python -m venv langgraph-env

# Activate it
# Linux/Mac:
source langgraph-env/bin/activate
# Windows:
# langgraph-env\Scripts\activate
```

#### Step 2: Install Core Packages
```bash
# Install LangGraph + LangChain core + OpenAI integration
pip install langgraph langchain-openai langchain-core

# Optional: For local LLMs via Ollama (no API key needed)
# pip install langchain-ollama
```

#### Step 3: Set Up Your API Key
```bash
# Set your OpenAI API key as an environment variable
export OPENAI_API_KEY="sk-your-key-here"

# Or create a .env file (recommended for projects)
echo 'OPENAI_API_KEY=sk-your-key-here' > .env
```

#### Step 4: Verify Installation
```python
# verify_setup.py — Confirms everything works
from langgraph.graph import StateGraph, START, END
# What: StateGraph is the main class for building workflows
# Why: If this import works, LangGraph is installed correctly

from typing import TypedDict

# Define a minimal state — just a message
class SimpleState(TypedDict):
    message: str

# Create the simplest possible graph
graph = StateGraph(SimpleState)

# Add one node that just passes through
def hello(state: SimpleState) -> dict:
    return {"message": "LangGraph is working! 🎉"}

graph.add_node("hello", hello)
graph.add_edge(START, "hello")
graph.add_edge("hello", END)

# Compile and run
app = graph.compile()
result = app.invoke({"message": ""})
print(result["message"])
# Expected output: LangGraph is working! 🎉
```

---

## Key Terms

- **Graph:** A workflow defined as nodes (steps) connected by edges (transitions)
- **State:** A typed dictionary that carries data through the entire graph execution
- **Node:** A Python function that receives state, does work, and returns state updates
- **Edge:** A connection between nodes — can be fixed or conditional
- **Checkpointer:** A persistence layer that saves graph state (enables memory, resume, time-travel)
- **Compile:** Locks the graph structure and returns a runnable object
- **Reducer:** A function that defines how state updates are merged (e.g., append vs. replace)

---

## Common Misunderstandings (Before You Start)

| ❌ Misconception | ✅ Reality |
|-----------------|-----------|
| "LangGraph replaces LangChain" | They're complementary — LangChain = components, LangGraph = orchestration |
| "It's only for chatbots" | It handles any stateful workflow: ETL, automation, multi-agent systems |
| "Graphs are complex" | A basic graph is ~20 lines of Python. Complexity is opt-in |
| "You need OpenAI" | Works with any LLM: Ollama, Anthropic, Google, HuggingFace |
| "It's just another wrapper" | It provides state management, persistence, and human-in-the-loop — things raw LLM APIs don't |

---

## Next Steps

→ **Module 01: Core Concepts** — Learn State, Nodes, Edges, and Reducers in depth with hands-on code

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-05 | Initial creation |
