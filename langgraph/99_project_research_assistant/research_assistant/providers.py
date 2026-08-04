"""Model selection — offline by default, local Ollama optionally.

LANGGRAPH_LLM=fake   (default) → deterministic FakeListChatModel, no network
LANGGRAPH_LLM=ollama           → local ChatOllama (needs `ollama pull qwen2.5:0.5b`)
"""
import os


def get_model(responses=None, temperature=0):
    backend = os.getenv("LANGGRAPH_LLM", "fake")
    if backend == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
                          temperature=temperature)
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    return FakeListChatModel(responses=responses or ["(fake response)"])
