"""Pick the embeddings model and chat model the app will use.

* Embeddings — a real local model (MiniLM, via langchain-huggingface) when it's
  installed; otherwise a deterministic fake so ingestion still works offline.
* Chat model — OpenAI by default (needs ``OPENAI_API_KEY``), or a local Ollama
  model when ``DOC_ASSISTANT_LLM=ollama``.

Which one you get is controlled by environment variables, so the rest of the app
never has to care.
"""

from __future__ import annotations

import os

from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings
from langchain_core.language_models.chat_models import BaseChatModel


def get_embeddings() -> Embeddings:
    """Real MiniLM embeddings if available, else a deterministic fake.

    Set ``DOC_ASSISTANT_FAKE_EMBEDDINGS=1`` to force the fake (used by the tests).
    """
    if os.environ.get("DOC_ASSISTANT_FAKE_EMBEDDINGS") == "1":
        return DeterministicFakeEmbedding(size=384)
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except Exception:  # library missing or model can't be downloaded
        return DeterministicFakeEmbedding(size=384)


def get_chat_model() -> BaseChatModel:
    """Return a chat model based on ``DOC_ASSISTANT_LLM`` (openai | ollama). Default: openai."""
    provider = os.environ.get("DOC_ASSISTANT_LLM", "openai").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=os.environ.get("OLLAMA_MODEL", "qwen2:7b"), temperature=0)

    # Default. Also works with any OpenAI-compatible endpoint (e.g. the free NVIDIA API):
    # set OPENAI_BASE_URL and put that provider's key in OPENAI_API_KEY.
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
        temperature=0,
    )
