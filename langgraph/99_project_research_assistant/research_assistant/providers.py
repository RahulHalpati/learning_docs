"""Model selection — OpenAI by default, local Ollama optionally.

LANGGRAPH_LLM=openai (default) → ChatOpenAI gpt-4o-mini (needs OPENAI_API_KEY)
LANGGRAPH_LLM=ollama           → local ChatOllama (needs `ollama pull qwen2.5:0.5b`)
"""
import os


def get_model(temperature=0):
    if os.getenv("LANGGRAPH_LLM", "openai") == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
                          temperature=temperature)
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=temperature)
