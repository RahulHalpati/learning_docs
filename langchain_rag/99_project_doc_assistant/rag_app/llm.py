"""Pick the embeddings model and chat model the app will use.

The app is designed to *always run*, even with no API key and no local model:

* Embeddings — a real local model (MiniLM, via langchain-huggingface) when it's
  installed; otherwise a deterministic fake so the pipeline still works offline.
* Chat model — a real local LLM (Ollama) or a hosted OpenAI-compatible endpoint
  when configured; otherwise a canned fake model so you can see the *shape* of an
  answer without any setup.

Which one you get is controlled by environment variables, so the rest of the app
never has to care.
"""

from __future__ import annotations

import os

from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings
from langchain_core.language_models import GenericFakeChatModel
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
    """Return a chat model based on ``DOC_ASSISTANT_LLM`` (ollama | openai | fake).

    Defaults to ``ollama`` if available, else falls back to a fake model so the
    app always produces *something* without setup.
    """
    provider = os.environ.get("DOC_ASSISTANT_LLM", "ollama").lower()

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama

            model = os.environ.get("OLLAMA_MODEL", "qwen2:7b")
            return ChatOllama(model=model, temperature=0)
        except Exception:
            provider = "fake"

    if provider == "openai":
        # Works with any OpenAI-compatible endpoint (e.g. the free NVIDIA API).
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=os.environ.get("OPENAI_BASE_URL"),  # e.g. NVIDIA's endpoint
            temperature=0,
        )

    # Fallback: a fake model that echoes a fixed answer. No network, no key.
    return GenericFakeChatModel(
        messages=iter(
            ["[fake LLM] Set DOC_ASSISTANT_LLM=ollama (or openai) for a real answer."]
        )
    )
