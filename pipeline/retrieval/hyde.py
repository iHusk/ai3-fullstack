"""
hyde.py -- Hypothetical Document Embeddings (HyDE)

HyDE transforms user queries by generating a *hypothetical* answer first,
then embedding that answer for retrieval instead of the raw question.

Why it works:
    Questions and answers live in different embedding neighborhoods.
    "What are Northbrook's consulting fees?" lands in question-space, but
    the actual fee schedule chunk lives in answer-space.  A naive embed of
    the question may never get close enough to surface the right chunk.

    HyDE bridges this "embedding gap" by asking the LLM to imagine what a
    correct answer might look like.  The hypothetical answer -- even though
    it may contain hallucinated details -- occupies the same embedding
    neighborhood as the real answer chunks.  We embed the hypothesis and
    search with it, pulling back the genuine documents that live nearby.

Session 1.1: We build these functions together in class.
"""

from pathlib import Path

import anthropic

from pipeline.embeddings.embed import embed_texts
from pipeline.ingestion.store import get_collection


def _get_client():
    """Lazy Anthropic client — instantiated on first call, after env keys are set."""
    return anthropic.Anthropic()


# ─── CUSTOMIZABLE: Hypothetical answer prompt ──────────────────────
# Change the system prompt or user prompt to improve hypothetical
# answers for your specific use case.
# ───────────────────────────────────────────────────────────────────

def generate_hypothetical_answer(question: str, domain: str = "company") -> str:
    """Ask Claude to imagine what a correct answer document would say.

    The generated text does NOT need to be factually correct -- it only
    needs to *sound like* a real document so its embedding lands in the
    right neighborhood.

    Args:
        question: The user's question.
        domain: Domain hint used in the prompt (default: "company").

    Returns:
        A short hypothetical answer string (2-3 sentences).
    """
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=256,
        system=(
            f"You are a technical writer producing internal {domain} documentation. "
            "Write as if you are quoting directly from an existing internal document. "
            "Be specific, use professional language, and do not hedge or qualify."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Answer this question in 2-3 sentences as if you were "
                    f"an internal {domain} document: {question}"
                ),
            }
        ],
    )

    return message.content[0].text


def hyde_retrieve(question: str, top_k: int = 5, domain: str = "company") -> list[dict]:
    """Retrieve chunks using a hypothetical answer embedding.

    Steps:
        1. Generate a hypothetical answer for the question.
        2. Embed the *hypothetical answer* (NOT the question).
        3. Query ChromaDB with the hypothetical embedding.
        4. Format results with text, metadata, score, and the hypothesis.

    Args:
        question: The user's question.
        top_k: Number of chunks to retrieve (default: 5).
        domain: Domain hint passed to the hypothesis generator.

    Returns:
        A list of dicts, each containing:
            - text: The chunk content.
            - metadata: The chunk's stored metadata.
            - score: Cosine similarity (1 - distance), higher is better.
            - hyde_answer: The hypothetical answer that was used for search.
    """
    # Step 1 -- Generate a hypothetical answer
    hyde_answer = generate_hypothetical_answer(question, domain)

    # Step 2 -- Embed the hypothesis (this is the key insight of HyDE)
    hyde_embedding = embed_texts([hyde_answer])[0]

    # Step 3 -- Query ChromaDB with the hypothetical embedding
    collection = get_collection()

    results = collection.query(
        query_embeddings=[hyde_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # Step 4 -- Format results
    sources = [
        {
            "text": doc,
            "metadata": meta,
            "score": 1 - dist,
            "hyde_answer": hyde_answer,
        }
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]

    sources.sort(key=lambda s: s["score"], reverse=True)

    return sources
