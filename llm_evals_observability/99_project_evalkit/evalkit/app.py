"""The system under test: a tiny, fully offline RAG pipeline.

Deliberately imperfect — it gets some questions right, some partially, and one
wrong — so the eval suite has something real to measure. `version` switches
between a weaker and a better retriever, which is how we demonstrate regression
detection in CI.
"""
from __future__ import annotations

from evalkit.metrics import _tokens
from evalkit.tracing import Trace

CORPUS = {
    "d1": "Flask is a Python micro-framework. Flask 3 uses the application factory pattern.",
    "d2": "FastAPI is an async Python framework built on Starlette and Pydantic.",
    "d3": "Alembic handles database migrations. Flask-Migrate wraps Alembic for Flask.",
    "d4": "Gunicorn is a production WSGI server. Never use the Flask dev server in production.",
    "d5": "Redis is an in-memory store used for caching, rate limiting and pub/sub.",
}


# Common words carry no topical signal. Counting them makes every document look
# "relevant" — the classic naive-retrieval bug that v1 still has.
STOPWORDS = {"a", "an", "the", "is", "are", "was", "were", "in", "on", "for",
             "of", "to", "what", "which", "who", "should", "i", "use", "used",
             "and", "it", "do", "does", "with"}


def retrieve(query: str, k: int = 2, version: str = "v2") -> list[str]:
    """Score documents by token overlap with the query; return the top-k doc ids.

    v1 — naive overlap, counts stopwords (so unrelated docs score > 0).
    v2 — filters stopwords, so an out-of-scope question retrieves nothing.
    """
    q = set(_tokens(query))
    if version == "v2":
        q -= STOPWORDS
    scored = []
    for doc_id, text in CORPUS.items():
        terms = set(_tokens(text))
        if version == "v2":
            terms -= STOPWORDS
        scored.append((doc_id, len(q & terms)))
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    return [doc_id for doc_id, score in scored[:k] if score > 0]


def generate(query: str, doc_ids: list[str]) -> tuple[str, int, int]:
    """Compose an answer from the retrieved context. Returns (answer, prompt_tok, completion_tok).

    Extractive on purpose: it returns the sentence in context that best matches
    the query, so faithfulness is high but completeness depends on retrieval.
    """
    if not doc_ids:
        return "I don't know.", 12, 4
    sentences: list[str] = []
    for doc_id in doc_ids:
        sentences.extend(s.strip() for s in CORPUS[doc_id].split(".") if s.strip())
    q = set(_tokens(query))
    best = max(sentences, key=lambda s: len(q & set(_tokens(s))))
    answer = best + "."
    # Token counts are proportional to text length — a stand-in for a tokenizer.
    prompt_tokens = sum(len(_tokens(CORPUS[d])) for d in doc_ids) + len(_tokens(query))
    return answer, prompt_tokens, len(_tokens(answer))


def answer_question(query: str, version: str = "v2", trace: Trace | None = None) -> dict:
    """Run the pipeline end to end, emitting spans if a trace is supplied."""
    trace = trace or Trace(name="rag.answer")
    with trace.span("retrieve", query=query, version=version) as s_ret:
        doc_ids = retrieve(query, version=version)
        s_ret.attributes["retrieved"] = doc_ids

    with trace.span("generate") as s_gen:
        answer, p_tok, c_tok = generate(query, doc_ids)
        model = "demo-small" if version == "v1" else "demo-large"
        trace.record_llm(s_gen, model=model, prompt_tokens=p_tok, completion_tokens=c_tok)

    return {
        "query": query,
        "answer": answer,
        "retrieved": doc_ids,
        "context": [CORPUS[d] for d in doc_ids],
        "trace": trace,
    }
