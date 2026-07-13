# 03: Practical Implementation (Python)

> **Level:** Beginner → Intermediate  
> **Prerequisites:** Modules 00–02  
> **Time:** 2–3 hours  
> **What You'll Learn:** Production-style code patterns from minimal to advanced  
> **Last Updated:** 2026-05-05

---

## Introduction

**What:** Hands-on code you can copy, run, and adapt for real projects.  
**Why:** Theory without code is useless. This module gives you three runnable examples of increasing complexity.  
**Approach:** Each example builds on the previous — minimal → tool-calling agent → multi-agent with memory.

---

## Setup (All Examples)

```bash
# Install everything you'll need for this module
pip install langgraph langchain-openai langchain-core langchain-community

# Set your API key
export OPENAI_API_KEY="sk-your-key-here"
```

```python
# common.py — Shared imports used across all examples
# STANDARD LIBRARY
from typing import TypedDict, Annotated, Literal
import operator  # What: operator.add for list reducers

# LANGGRAPH CORE
from langgraph.graph import StateGraph, START, END, MessagesState
# What: Graph builder + sentinel nodes + pre-built chat state
from langgraph.graph import add_messages
# What: Built-in reducer that appends messages intelligently
from langgraph.checkpoint.memory import MemorySaver
# What: In-memory checkpoint storage (dev only)
from langgraph.prebuilt import ToolNode, tools_condition
# What: Pre-built utilities for tool-calling agents

# LANGCHAIN
from langchain_openai import ChatOpenAI
# What: OpenAI LLM wrapper | Install: pip install langchain-openai
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# What: Typed message objects for chat history
from langchain_core.tools import tool
# What: Decorator to turn functions into LangChain tools
```

---

## Example 1: Minimal — Simple Chatbot (No Tools)

**Goal:** The simplest possible chatbot with conversation memory.  
**Concepts used:** MessagesState, single node, checkpointer, thread_id.

```python
"""
minimal_chatbot.py
What: A chatbot that remembers conversation history across turns
Why: The "hello world" of LangGraph — fewest lines to a working agent
"""

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI


# ── 1. Define the single node ──
def chatbot(state: MessagesState) -> dict:
    """
    What: Takes conversation history, generates a response.
    Why: This is the core loop of any chatbot.

    Args:
        state: Contains 'messages' — full conversation history
    Returns:
        dict with 'messages' key — LangGraph appends via add_messages reducer
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    response = llm.invoke(state["messages"])
    # Return as list — add_messages reducer appends to existing messages
    return {"messages": [response]}


# ── 2. Build the graph ──
builder = StateGraph(MessagesState)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

# ── 3. Compile with memory ──
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

# ── 4. Run a multi-turn conversation ──
config = {"configurable": {"thread_id": "demo-001"}}
# thread_id isolates this conversation from others

# Turn 1
response = graph.invoke(
    {"messages": [("user", "My name is Alex. I'm learning LangGraph.")]},
    config=config
)
print(response["messages"][-1].content)

# Turn 2 — the bot REMEMBERS turn 1 (same thread_id)
response = graph.invoke(
    {"messages": [("user", "What's my name and what am I learning?")]},
    config=config
)
print(response["messages"][-1].content)
# Expected: "Your name is Alex and you're learning LangGraph!"
```

**Expected Output:**
```
Nice to meet you, Alex! LangGraph is a great choice...
Your name is Alex and you're learning LangGraph!
```

---

## Example 2: Intermediate — Tool-Calling Agent (ReAct Pattern)

**Goal:** An agent that can call external tools (search, calculator) and reason about when to use them.  
**Concepts used:** Tools, ToolNode, conditional edges, the ReAct loop.

```python
"""
tool_agent.py
What: An agent that decides when to use tools and when to respond directly
Why: Most production agents need to interact with external systems
Pattern: ReAct (Reason + Act) — the LLM decides, tools execute, LLM synthesizes
"""

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
# What: ToolNode — pre-built node that executes tool calls from LLM output
# What: tools_condition — pre-built router: "tools" if LLM wants tools, END otherwise
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool


# ── 1. Define Tools ──
@tool
def search_web(query: str) -> str:
    """Search the web for current information about a topic.

    Args:
        query: The search query string
    """
    # Simulated — replace with real search API (Tavily, SerpAPI, etc.)
    return f"Search results for '{query}': LangGraph is a framework by LangChain for building stateful AI agents. Latest version supports async, streaming, and multi-agent patterns."


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: A valid Python math expression (e.g., '2 + 2', '100 * 0.15')
    """
    try:
        result = eval(expression)  # Safe in this context — production should use ast.literal_eval
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error evaluating '{expression}': {e}"


# ── 2. Create LLM with tools bound ──
tools = [search_web, calculator]
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(tools)
# bind_tools: Tells the LLM about available tools so it can request them
# The LLM doesn't CALL tools — it outputs a structured request
# LangGraph's ToolNode handles the actual execution


# ── 3. Define Nodes ──
def agent(state: MessagesState) -> dict:
    """
    What: The 'brain' — decides whether to use a tool or respond directly.
    Why: Central decision-maker in the ReAct loop.

    The LLM sees the full conversation (including tool results) and either:
    - Generates a tool_call → routed to ToolNode
    - Generates a text response → routed to END
    """
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


# ── 4. Build the ReAct Graph ──
builder = StateGraph(MessagesState)

# Add nodes
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(tools))
# ToolNode: Pre-built node that:
#   1. Reads tool_call requests from the last AI message
#   2. Executes the matching tool function
#   3. Returns the result as a ToolMessage

# Add edges
builder.add_edge(START, "agent")

# The ReAct loop: agent → tools → agent → tools → ... → END
builder.add_conditional_edges(
    "agent",
    tools_condition,
    # tools_condition is equivalent to:
    # def tools_condition(state):
    #     last_msg = state["messages"][-1]
    #     if last_msg.tool_calls:   # LLM wants to use tools
    #         return "tools"
    #     return END                # LLM is done, respond to user
)
builder.add_edge("tools", "agent")
# After tools execute, go BACK to agent so it can:
# - See the tool results
# - Decide to call more tools or give final answer

# ── 5. Compile & Run ──
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "agent-001"}}

# Test 1: Tool usage (search)
response = graph.invoke(
    {"messages": [("user", "What is LangGraph? Search for it.")]},
    config=config
)
print("Agent:", response["messages"][-1].content)

# Test 2: Tool usage (calculator)
response = graph.invoke(
    {"messages": [("user", "What's 15% tip on a $85 dinner?")]},
    config=config
)
print("Agent:", response["messages"][-1].content)

# Test 3: No tool needed (direct response)
response = graph.invoke(
    {"messages": [("user", "Thanks! What did we discuss earlier?")]},
    config=config
)
print("Agent:", response["messages"][-1].content)
```

**ReAct Loop Visualized:**
```
User: "What is LangGraph?"
  │
  ▼
┌─────────┐   tool_calls exist    ┌──────────┐
│  agent   │ ──────────────────▶  │  tools   │
│ (LLM)   │                      │ (execute)│
│          │ ◀────────────────── │          │
└────┬─────┘   tool results       └──────────┘
     │
     │ no tool_calls (final answer)
     ▼
   END → "LangGraph is a framework..."
```

---

## Example 3: Advanced — Multi-Agent with Supervisor

**Goal:** Multiple specialized agents coordinated by a supervisor agent.  
**Concepts used:** Subgraphs, supervisor pattern, structured routing, all prior concepts.

```python
"""
multi_agent_supervisor.py
What: A supervisor agent that routes tasks to specialized worker agents
Why: Complex tasks benefit from specialized agents (divide and conquer)
Pattern: Supervisor — one LLM decides which specialist handles each step
"""

from typing import TypedDict, Annotated, Literal
import operator
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


# ── 1. Define Shared State ──
class TeamState(TypedDict):
    messages: Annotated[list, operator.add]
    # Full conversation history — shared across all agents

    next_agent: str
    # Who should act next — set by supervisor

    research_output: str
    # Output from researcher agent

    writing_output: str
    # Output from writer agent


# ── 2. Define Specialist Agents ──
def researcher(state: TeamState) -> dict:
    """
    What: Specialist agent focused on finding and analyzing information.
    Why: Separating research from writing produces better results.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    # Give the researcher a focused system prompt
    research_messages = [
        SystemMessage(content=(
            "You are a research specialist. Your job is to find key facts, "
            "data points, and insights about the given topic. Be thorough "
            "and cite specific details. Output structured findings."
        )),
        *state["messages"]  # Include conversation context
    ]

    response = llm.invoke(research_messages)
    return {
        "research_output": response.content,
        "messages": [response]
    }


def writer(state: TeamState) -> dict:
    """
    What: Specialist agent focused on producing polished written content.
    Why: A writer that receives pre-researched material produces higher quality output.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    writing_messages = [
        SystemMessage(content=(
            "You are a professional writer. Use the research provided to "
            "create clear, engaging, well-structured content. "
            f"Research to use:\n{state.get('research_output', 'No research yet.')}"
        )),
        *state["messages"]
    ]

    response = llm.invoke(writing_messages)
    return {
        "writing_output": response.content,
        "messages": [response]
    }


def supervisor(state: TeamState) -> dict:
    """
    What: Coordinator that decides which specialist should act next.
    Why: Central orchestration ensures tasks are routed to the right expert.

    The supervisor examines the current state and decides:
    - "researcher" → need more information
    - "writer"     → ready to write
    - "FINISH"     → task is complete
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    supervisor_messages = [
        SystemMessage(content=(
            "You are a team supervisor managing a researcher and a writer. "
            "Based on the conversation, decide who should act next.\n"
            "- If the task needs research/facts, choose 'researcher'\n"
            "- If research is done and we need written output, choose 'writer'\n"
            "- If the final output has been produced, choose 'FINISH'\n\n"
            "Respond with ONLY one word: researcher, writer, or FINISH"
        )),
        *state["messages"]
    ]

    response = llm.invoke(supervisor_messages)
    next_agent = response.content.strip().lower()

    # Normalize the response
    if "research" in next_agent:
        next_agent = "researcher"
    elif "writ" in next_agent:
        next_agent = "writer"
    else:
        next_agent = "FINISH"

    return {"next_agent": next_agent}


# ── 3. Build the Supervisor Graph ──
def route_supervisor(state: TeamState) -> Literal["researcher", "writer", "FINISH"]:
    """Routes to the next agent based on supervisor's decision."""
    return state.get("next_agent", "FINISH")


builder = StateGraph(TeamState)

# Add all agent nodes
builder.add_node("supervisor", supervisor)
builder.add_node("researcher", researcher)
builder.add_node("writer", writer)

# Flow: START → supervisor → (agent) → supervisor → ... → END
builder.add_edge(START, "supervisor")

builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "researcher": "researcher",
        "writer": "writer",
        "FINISH": END,
    }
)

# After any specialist finishes, go back to supervisor for next decision
builder.add_edge("researcher", "supervisor")
builder.add_edge("writer", "supervisor")


# ── 4. Compile & Run ──
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "team-001"}}

# Give the team a task
result = graph.invoke(
    {
        "messages": [
            HumanMessage(content="Write a brief article about the impact of AI agents in enterprise software in 2025.")
        ],
        "next_agent": "",
        "research_output": "",
        "writing_output": "",
    },
    config=config
)

print("=" * 60)
print("FINAL OUTPUT")
print("=" * 60)
print(result.get("writing_output", "No output"))
```

**Supervisor Flow:**
```
User Task
   │
   ▼
┌────────────┐    "researcher"     ┌────────────┐
│ Supervisor  │ ─────────────────▶ │ Researcher  │
│ (decides)   │ ◀───────────────── │ (finds data)│
│             │                    └────────────┘
│             │    "writer"        ┌────────────┐
│             │ ─────────────────▶ │   Writer    │
│             │ ◀───────────────── │ (produces)  │
│             │                    └────────────┘
│             │    "FINISH"
│             │ ─────────────────▶ END
└────────────┘
```

---

## Quick-Start with `create_react_agent`

For simple tool-calling agents, LangGraph provides a **one-liner** shortcut:

```python
"""
quick_react.py
What: Fastest way to get a tool-calling agent running
Why: Skip manual graph building when you just need a basic ReAct agent
"""
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"Weather in {city}: 22°C, partly cloudy"


# ONE LINE to create a full ReAct agent with tools + memory
agent = create_react_agent(
    model=ChatOpenAI(model="gpt-4o-mini"),
    tools=[get_weather],
    checkpointer=MemorySaver(),
)

# Use it
config = {"configurable": {"thread_id": "weather-001"}}
result = agent.invoke(
    {"messages": [("user", "What's the weather in London?")]},
    config=config
)
print(result["messages"][-1].content)
# Expected: "The weather in London is 22°C, partly cloudy."
```

> **When to use `create_react_agent` vs custom graph:**  
> - **Use `create_react_agent`** for standard tool-calling agents — saves 20+ lines  
> - **Build custom** when you need custom routing, multiple agent types, or non-standard flows

---

## What's Next

**Learned:** ✅ Minimal chatbot, ✅ ReAct tool-calling agent, ✅ Multi-agent supervisor, ✅ `create_react_agent` shortcut  
**Next:** Module 04: Real-World Use Cases — Chatbot, RAG agent, automation pipeline  
**Check:** Can you modify Example 2 to add a new tool? Can you add a third specialist to Example 3?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-05 | Initial creation |
