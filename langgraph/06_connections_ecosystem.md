# 06: Connections & Ecosystem — How LangGraph Relates to Everything Else

> **Level:** Intermediate  
> **Prerequisites:** Modules 00–05  
> **Time:** 45–60 minutes  
> **What You'll Learn:** How LangGraph connects to agents, RAG, tools, memory, orchestration, and the broader LangChain ecosystem  
> **Last Updated:** 2026-05-05

---

## Introduction

**What:** A map of how LangGraph fits alongside — and integrates with — every major concept in modern AI engineering.  
**Why:** LangGraph doesn't exist in isolation. Knowing where it ends and other tools begin is the difference between a clean architecture and a tangled mess.  
**Analogy:** Think of LangGraph as the **conductor** of an orchestra. It doesn't play every instrument (LangChain tools, vector stores, LLMs), but it decides *when* each instrument plays, *how loud*, and *in what order*.

---

## 🔗 The LangChain Ecosystem Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        YOUR APPLICATION                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────────┐        ┌──────────────────────────────────┐ │
│   │   LangChain       │        │          LangGraph                │ │
│   │   (Components)     │        │    (Orchestration Engine)        │ │
│   │                    │        │                                  │ │
│   │   • ChatModels     │───────▶│   • StateGraph (workflow def)   │ │
│   │   • Tools          │        │   • Nodes (execution units)     │ │
│   │   • Retrievers     │        │   • Edges (routing logic)       │ │
│   │   • Embeddings     │        │   • Checkpointers (persistence) │ │
│   │   • Prompts        │        │   • HITL (human approval)       │ │
│   │   • Document       │        │   • Subgraphs (modularity)      │ │
│   │     Loaders        │        │   • Streaming (real-time)       │ │
│   └──────────────────┘        └──────────┬───────────────────────┘ │
│                                           │                         │
│   ┌──────────────────┐        ┌──────────▼───────────────────────┐ │
│   │   LangSmith       │◀───────│      LangGraph Platform          │ │
│   │   (Observability)  │        │   (Managed Deployment)           │ │
│   │                    │        │                                  │ │
│   │   • Tracing        │        │   • LangGraph Cloud             │ │
│   │   • Evaluations    │        │   • LangGraph CLI (self-host)   │ │
│   │   • Datasets       │        │   • Cron jobs, webhooks         │ │
│   │   • Monitoring     │        │   • Built-in persistence        │ │
│   └──────────────────┘        └──────────────────────────────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│   LLM Providers:  OpenAI │ Anthropic │ Google │ Ollama │ Others    │
│   Vector Stores:  Pinecone │ Chroma │ Weaviate │ pgvector          │
│   Databases:      PostgreSQL │ Redis │ MongoDB                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Quick Reference: Who Does What?

| Component | Role | Analogy |
|-----------|------|---------|
| **LangChain** | Individual AI building blocks (LLMs, tools, retrievers) | LEGO bricks |
| **LangGraph** | Orchestrates those blocks into stateful workflows | The instruction manual |
| **LangSmith** | Observability — traces, evaluates, monitors | The quality inspector |
| **LangGraph Platform** | Deployment + hosting of LangGraph apps | The factory floor |
| **LLM Providers** | The underlying models (GPT, Claude, Gemini) | The raw materials |
| **Vector Stores** | Storage + retrieval for embeddings (RAG) | The filing cabinet |

---

## 🤖 Connection 1: LangGraph ↔ Agents

**Relationship:** LangGraph **is** the agent runtime. An "agent" in the LangChain ecosystem is a LangGraph graph.

### What Changed (2024 → 2026)

```
BEFORE (LangChain AgentExecutor — deprecated):
  User → AgentExecutor → LLM → Tool → LLM → Output
  ❌ No state persistence
  ❌ No human-in-the-loop
  ❌ No conditional routing
  ❌ Linear chain only

AFTER (LangGraph — current standard):
  User → StateGraph → Node(LLM) → Edge(conditional) → Node(Tool) → ...
  ✅ Full state management
  ✅ Human-in-the-loop
  ✅ Conditional routing + loops
  ✅ Multi-agent coordination
```

### Three Agent Patterns in LangGraph

```python
# ── Pattern 1: ReAct Agent (most common) ──
# One LLM decides + acts in a loop
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model=ChatOpenAI(model="gpt-4o-mini"),
    tools=[search, calculator],
    checkpointer=MemorySaver(),
)
# Use case: General-purpose assistant, chatbot with tools


# ── Pattern 2: Supervisor Agent ──
# One LLM delegates to specialist LLMs
# Supervisor node → routes to → Researcher | Writer | Analyst
# Each specialist is a node (or subgraph) with its own prompt
# Use case: Complex tasks requiring domain expertise
# (See Module 03, Example 3 for full implementation)


# ── Pattern 3: Hierarchical Multi-Agent ──
# Supervisors managing supervisors (nested subgraphs)
# Top Supervisor → Team A Supervisor → Workers
#                → Team B Supervisor → Workers
# Use case: Enterprise systems with multiple departments/domains
```

**Key Insight:** As of 2026, the LangChain team recommends implementing the supervisor pattern **directly with tool-calling** rather than using the `langgraph-supervisor` library. This gives more control over context engineering and prompt tuning.

---

## 📚 Connection 2: LangGraph ↔ RAG

**Relationship:** LangGraph adds **intelligence** to RAG pipelines. Simple RAG is a chain; production RAG is a graph.

### Simple RAG vs LangGraph RAG

```
SIMPLE RAG (LangChain chain — no graph):
  Query → Retrieve → Generate → Output
  ❌ No quality check
  ❌ No retry
  ❌ Can't refine query
  ❌ Single retrieval attempt

LANGGRAPH RAG (graph with loops):
  Query → Retrieve → Generate → Evaluate ──┐
    ▲                                        │
    │        quality = "retry"               │
    └────────────────────────────────────────┘
                    │
           quality = "good"
                    │
                    ▼
                  Output
  ✅ Self-correction loop
  ✅ Query refinement
  ✅ Multi-source retrieval
  ✅ Quality-gated output
```

### Where LangGraph Adds Value to RAG

| RAG Feature | Without LangGraph | With LangGraph |
|-------------|-------------------|----------------|
| **Retrieval** | Single-shot | Multi-step, query refinement |
| **Quality** | No validation | Self-evaluation + retry |
| **Sources** | Single vector store | Multiple stores, web search, APIs |
| **Routing** | One-size-fits-all | Route by query type (factual, opinion, code) |
| **Fallback** | Silent failure | Graceful degradation with alternatives |

```python
# Example: Multi-source RAG with query routing
def query_router(state) -> Literal["vector_search", "web_search", "sql_query"]:
    """Routes to the best retrieval source based on query type."""
    if "latest" in state["query"] or "current" in state["query"]:
        return "web_search"       # Time-sensitive → web
    if "how many" in state["query"] or "count" in state["query"]:
        return "sql_query"        # Quantitative → database
    return "vector_search"        # General knowledge → vector store
```

---

## 🔧 Connection 3: LangGraph ↔ Tools

**Relationship:** LangChain defines tools. LangGraph executes them at the right time.

### How Tools Flow Through a Graph

```
LLM decides tool is needed
        │
        ▼
┌───────────────────────────────┐
│  AIMessage with tool_calls    │  ← LLM outputs structured request
│  tool_calls: [{               │
│    name: "search_web",        │
│    args: {"query": "..."}     │
│  }]                           │
└───────────┬───────────────────┘
            │
            ▼ (conditional edge: tools_condition)
┌───────────────────────────────┐
│  ToolNode                     │  ← Executes the function
│  1. Reads tool_calls          │
│  2. Matches to registered fn  │
│  3. Calls fn with args        │
│  4. Returns ToolMessage       │
└───────────┬───────────────────┘
            │
            ▼ (edge back to agent)
┌───────────────────────────────┐
│  Agent node (LLM)             │  ← Sees tool result, decides next step
│  Has full context:            │
│  User msg + AI msg + Tool msg │
└───────────────────────────────┘
```

### Tool Integration Patterns

```python
from langchain_core.tools import tool
# What: Decorator that turns any function into a LangChain tool
# Why: Tools let LLMs interact with external systems

# Pattern 1: Simple function tool
@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"22°C, partly cloudy in {city}"

# Pattern 2: Tool with structured input (Pydantic)
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="The search query")
    max_results: int = Field(default=5, description="Maximum results to return")

@tool(args_schema=SearchInput)
def search_docs(query: str, max_results: int = 5) -> str:
    """Search internal documentation."""
    return f"Found {max_results} results for: {query}"

# Pattern 3: Async tool (for I/O-bound operations)
@tool
async def fetch_api_data(endpoint: str) -> str:
    """Fetch data from an external API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint) as resp:
            return await resp.text()
```

**Key Rule:** Tools are **defined** in LangChain, **bound** to LLMs via `.bind_tools()`, and **executed** inside LangGraph via `ToolNode`. The LLM never calls tools directly — it emits structured requests that the graph orchestrates.

---

## 🧠 Connection 4: LangGraph ↔ Memory

**Relationship:** LangGraph's checkpointer IS the memory system. There is no separate "memory" module.

### Memory Types in LangGraph

```
┌─────────────────────────────────────────────────────┐
│                    MEMORY IN LANGGRAPH               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  SHORT-TERM (Within a thread)                       │
│  ┌─────────────────────────────────────────────┐   │
│  │  Checkpointer + thread_id                    │   │
│  │  • Messages within a conversation            │   │
│  │  • State accumulated across turns            │   │
│  │  • Automatic — just use a checkpointer       │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  LONG-TERM (Across threads)                         │
│  ┌─────────────────────────────────────────────┐   │
│  │  Store (key-value persistence)               │   │
│  │  • User preferences across conversations    │   │
│  │  • Learned facts about the user              │   │
│  │  • Shared knowledge base                     │   │
│  │  • Requires explicit read/write in nodes     │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

```python
from langgraph.store.memory import InMemoryStore
# What: Key-value store for cross-thread memory
# Why: Remember facts about users across separate conversations

# ── Short-term: Conversation memory (automatic) ──
config = {"configurable": {"thread_id": "conv-001"}}
graph.invoke({"messages": [("user", "I'm Alex")]}, config)
graph.invoke({"messages": [("user", "What's my name?")]}, config)
# ✅ Remembers "Alex" within the same thread

# ── Long-term: Cross-conversation memory (explicit) ──
store = InMemoryStore()

def chatbot_with_memory(state, config, *, store):
    """Node that reads and writes long-term memory."""
    user_id = config["configurable"]["user_id"]

    # READ: Get stored facts about this user
    memories = store.search(("user_facts", user_id))
    memory_context = "\n".join(m.value["fact"] for m in memories)

    # Use memories in LLM prompt
    response = llm.invoke([
        SystemMessage(f"Known facts about user:\n{memory_context}"),
        *state["messages"]
    ])

    # WRITE: Extract and store new facts
    # (In production, use an LLM to extract facts from the conversation)
    store.put(
        ("user_facts", user_id),
        key=f"fact-{len(memories)}",
        value={"fact": "User prefers dark mode"}
    )

    return {"messages": [response]}

graph = builder.compile(checkpointer=MemorySaver(), store=store)
```

### Memory Decision Matrix

| Question | Answer | Memory Type |
|----------|--------|-------------|
| Do I need to remember within a conversation? | Yes | **Checkpointer** (automatic) |
| Do I need to remember across conversations? | Yes | **Store** (explicit read/write) |
| Do I need to remember across all users? | Yes | **External DB** (RAG / knowledge base) |

---

## 🎭 Connection 5: LangGraph ↔ Multi-Agent Orchestration

**Relationship:** LangGraph provides the **primitives** for multi-agent systems. Orchestration patterns are built *on top of* LangGraph.

### Orchestration Patterns

```
Pattern 1: SUPERVISOR (centralized)
┌────────────┐
│ Supervisor  │── routes to ──▶ Agent A
│ (decides)   │── routes to ──▶ Agent B
│             │── routes to ──▶ Agent C
└────────────┘
Best for: Tasks with clear subtask boundaries
Example: Research → Write → Review

Pattern 2: SWARM (decentralized — handoff-based)
Agent A ──handoff──▶ Agent B ──handoff──▶ Agent C
                         │
                         └──handoff──▶ Agent A
Best for: Tasks where context determines the next expert
Example: Customer support (billing → technical → account)

Pattern 3: MAP-REDUCE (parallel)
                    ┌── Agent A ──┐
Input ── fan out ── ├── Agent B ──├── merge ── Output
                    └── Agent C ──┘
Best for: Tasks that can be decomposed into independent subtasks
Example: Analyze 10 documents in parallel, then synthesize
```

### Subgraphs: The Modularity Primitive

```python
# Subgraphs let you nest graphs inside graphs
# Each subgraph is an independent state machine

# ── Define a subgraph (reusable component) ──
def build_research_subgraph():
    """Creates a self-contained research workflow."""

    class ResearchSubState(TypedDict):
        query: str
        findings: Annotated[list[str], operator.add]

    builder = StateGraph(ResearchSubState)
    builder.add_node("search", search_fn)
    builder.add_node("analyze", analyze_fn)
    builder.add_edge(START, "search")
    builder.add_edge("search", "analyze")
    builder.add_edge("analyze", END)
    return builder.compile()


# ── Use the subgraph in a parent graph ──
research_graph = build_research_subgraph()

parent_builder = StateGraph(ParentState)
parent_builder.add_node("research", research_graph)  # Subgraph as a node!
parent_builder.add_node("write_report", write_report_fn)
parent_builder.add_edge(START, "research")
parent_builder.add_edge("research", "write_report")
parent_builder.add_edge("write_report", END)
```

---

## 📡 Connection 6: LangGraph ↔ Deployment (LangGraph Platform)

**Relationship:** LangGraph Platform is the official deployment layer. It turns your graph into a production service.

### Deployment Options

| Option | Description | Best For |
|--------|-------------|----------|
| **LangGraph Cloud** | Fully managed hosting by LangChain Inc. | Teams wanting zero-ops |
| **Self-Hosted (langgraph-cli)** | Docker-based deployment on your infra | Enterprise with compliance needs |
| **DIY (FastAPI + graph)** | Manual wrapping in any web framework | Maximum flexibility |

```python
# ── Option 3: DIY with FastAPI (most control) ──
from fastapi import FastAPI
from langgraph.checkpoint.postgres import PostgresSaver

app = FastAPI()

# Build graph once at startup
DB_URI = "postgresql://user:pass@localhost:5432/langgraph"
checkpointer = PostgresSaver.from_conn_string(DB_URI)
checkpointer.setup()
graph = build_my_graph(checkpointer=checkpointer)


@app.post("/chat")
async def chat(user_id: str, message: str):
    config = {"configurable": {"thread_id": f"user-{user_id}"}}
    result = await graph.ainvoke(
        {"messages": [("user", message)]},
        config=config
    )
    return {"response": result["messages"][-1].content}
```

---

## 🔍 Connection 7: LangGraph ↔ LangSmith (Observability)

**Relationship:** LangSmith traces every node execution in your graph. Think of it as a debugger + profiler for AI workflows.

### What LangSmith Shows You

```
Trace: "user-123 conversation"
├── START
├── Node: classify_intent  [342ms]
│   ├── LLM Call: gpt-4o-mini  [298ms]
│   │   ├── Input: "Classify this customer's intent..."
│   │   └── Output: "account"
│   └── State Update: {"intent": "account"}
├── Node: handle_account  [567ms]
│   ├── LLM Call: gpt-4o-mini  [512ms]
│   │   ├── Input: "You are an account specialist..."
│   │   ├── Tool Call: check_account_balance("C001")
│   │   └── Tool Result: "$1,250.00"
│   └── State Update: {"messages": [...], "intent": "resolved"}
└── END  [Total: 934ms]
```

```python
# Enable with just 3 environment variables
import os
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "ls-your-key"
os.environ["LANGSMITH_PROJECT"] = "my-langgraph-app"

# Every graph.invoke() is now automatically traced
# View at: https://smith.langchain.com
```

### What to Monitor in Production

| Metric | Why | Alert Threshold |
|--------|-----|-----------------|
| **Node latency** | Identify slow LLM calls | > 5s for any single node |
| **Loop iterations** | Catch near-infinite loops | > configured MAX_RETRIES |
| **Token usage** | Cost control | > budget per conversation |
| **Error rate** | Node failures | > 5% of invocations |
| **Checkpoint size** | State bloat | > 1MB per checkpoint |

---

## 🗺️ Concept Relationship Map

```mermaid
graph TD
    subgraph LangGraph["LangGraph (Orchestration)"]
        SG["StateGraph"]
        N["Nodes"]
        E["Edges"]
        CP["Checkpointer"]
        HITL["Human-in-the-Loop"]
        SUB["Subgraphs"]
    end

    subgraph LangChain["LangChain (Components)"]
        LLM["ChatModels"]
        T["Tools"]
        R["Retrievers"]
        EMB["Embeddings"]
    end

    subgraph Deployment["Deployment"]
        LGP["LangGraph Platform"]
        FA["FastAPI / Django"]
        LS["LangSmith"]
    end

    subgraph Patterns["Application Patterns"]
        AG["Agents"]
        RAG["RAG Pipelines"]
        MA["Multi-Agent Systems"]
        AUTO["Automation"]
    end

    LLM --> N
    T --> N
    R --> N
    N --> SG
    E --> SG
    CP --> SG
    HITL --> SG
    SUB --> SG

    SG --> AG
    SG --> RAG
    SG --> MA
    SG --> AUTO

    SG --> LGP
    SG --> FA
    LGP --> LS
    FA --> LS
```

---

## Best Practices

**✅ DO:**
- Use LangChain components inside LangGraph nodes — Why: LangChain handles LLM/tool abstractions, LangGraph handles orchestration
- Enable LangSmith tracing from day one — Why: Debugging agentic systems without traces is nearly impossible
- Use subgraphs for complex multi-agent systems — Why: Isolation, testability, reusability
- Plan your memory strategy early (short-term vs long-term) — Why: Retrofitting memory into an existing graph is painful

**❌ DON'T:**
- Mix orchestration logic with component logic — Why bad: Makes graphs brittle and hard to test | Fix: Clean separation — nodes do work, edges decide flow
- Use LangChain's deprecated `AgentExecutor` — Why bad: No state, no HITL, no persistence | Fix: Use LangGraph's `create_react_agent` or custom StateGraph
- Build multi-agent systems without observability — Why bad: Impossible to debug inter-agent communication | Fix: LangSmith or Langfuse from the start
- Skip the checkpointer for "simple" apps — Why bad: You'll need persistence sooner than you think | Fix: Start with MemorySaver, upgrade to Postgres

---

## What's Next

**Learned:** ✅ LangGraph ↔ Agents, ✅ LangGraph ↔ RAG, ✅ LangGraph ↔ Tools, ✅ LangGraph ↔ Memory, ✅ LangGraph ↔ Multi-Agent, ✅ LangGraph ↔ Deployment, ✅ LangGraph ↔ LangSmith  
**Next:** Module 07: Mini Project — Build a complete Research Assistant agent  
**Check:** Can you draw the boundary between LangChain and LangGraph in your own project? Can you explain when to use a subgraph vs a simple node?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-05 | Initial creation |
