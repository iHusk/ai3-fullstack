"""
reranker.py -- Cross-encoder reranking via Voyage rerank-2.

After bi-encoder retrieval (naive or HyDE) returns the top-N candidates by
cosine similarity, the reranker re-scores each (query, chunk) pair JOINTLY
using a cross-encoder. Cross-encoders are slower per pair but far more
accurate at judging relevance, because they see the query and the candidate
together rather than projecting each into an embedding space first.

Standard pattern:
    candidates = retrieve(query, top_k=20)   # cheap recall
    top_k      = rerank(query, candidates, top_k=5)   # precision

If the rerank API errors, we fall back to the original similarity ordering
truncated to top_k. The pipeline never hard-fails on a reranker outage.
"""

from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)

import voyageai


RERANK_MODEL = "rerank-2"


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    model: str = RERANK_MODEL,
) -> list[dict]:
    """Re-score retrieved candidates with a cross-encoder and return the best top_k.

    Args:
        query: The user's question (or rewritten/standalone query).
        candidates: List of dicts from retrieve() with at minimum a ``text`` key.
        top_k: How many to keep after reranking.
        model: Voyage rerank model name.

    Returns:
        A list of up to ``top_k`` dicts, ordered by rerank score (descending).
        Each dict gets a new ``rerank_score`` key; original ``score`` is preserved
        for traceability. On API failure, falls back to the input ordering.
    """
    if not candidates:
        return []

    if len(candidates) <= top_k:
        try:
            return _do_rerank(query, candidates, len(candidates), model)
        except Exception:
            return candidates

    try:
        return _do_rerank(query, candidates, top_k, model)
    except Exception:
        return candidates[:top_k]


def _do_rerank(
    query: str,
    candidates: list[dict],
    top_k: int,
    model: str,
) -> list[dict]:
    client = voyageai.Client()
    documents = [c["text"] for c in candidates]

    result = client.rerank(
        query=query,
        documents=documents,
        model=model,
        top_k=top_k,
    )

    reranked = []
    for item in result.results:
        original = candidates[item.index]
        reranked.append({**original, "rerank_score": float(item.relevance_score)})
    return reranked
