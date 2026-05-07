"""
embed.py -- Wrapper for generating embeddings via the Voyage AI API.

This module provides functions for creating vector embeddings and
comparing them with cosine similarity.

Available Voyage AI models:
  - voyage-3-lite: 1024 dims, fastest, cheapest
  - voyage-3:      1024 dims, balanced
  - voyage-3-large: 2048 dims, highest quality, most expensive

Usage:
    from pipeline.embeddings.embed import get_embedding, embed_texts, cosine_similarity

    vec = get_embedding("What is machine learning?")
    vecs = embed_texts(["sentence one", "sentence two"])
    score = cosine_similarity(vecs[0], vecs[1])
"""

import voyageai
import numpy as np
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE = 128


def _get_voyage_client():
    """Lazy Voyage AI client.

    Inside a Streamlit script run: requires the per-session key in
    ``st.session_state["voyage_key"]``. Raises if it is not set,
    so we never silently fall through to the deploy's process env
    (which would bill whichever key happens to be cached there).

    Outside Streamlit (notebooks, scripts, tests): falls back to the
    ``VOYAGE_API_KEY`` env var so existing usage keeps working.
    """
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        in_streamlit = get_script_run_ctx() is not None
    except Exception:
        in_streamlit = False

    if in_streamlit:
        import streamlit as st
        key = st.session_state.get("voyage_key", "")
        if not key:
            raise RuntimeError(
                "Voyage API key not found in session state. "
                "Enter your key in the sidebar to continue."
            )
        return voyageai.Client(api_key=key)

    return voyageai.Client()


def get_embedding(text: str, model: str = "voyage-3-lite") -> list[float]:
    """Generate an embedding vector for a single piece of text.

    Args:
        text: The text to embed.
        model: Voyage AI model to use (default: voyage-3-lite).

    Returns:
        A list of floats representing the embedding vector.
    """
    client = _get_voyage_client()

    result = client.embed(texts=[text], model=model)

    return result.embeddings[0]


def embed_texts(texts: list[str], model: str = "voyage-3-lite") -> list[list[float]]:
    """Generate embedding vectors for a list of texts.

    Handles batching automatically -- Voyage AI limits the number of texts
    per request, so this function sends them in groups of 128.

    Args:
        texts: The list of texts to embed.
        model: Voyage AI model to use (default: voyage-3-lite).

    Returns:
        A list of embedding vectors, one per input text.
    """
    client = _get_voyage_client()

    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        result = client.embed(texts=batch, model=model)
        all_embeddings.extend(result.embeddings)

    return all_embeddings


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute the cosine similarity between two vectors.

    Cosine similarity measures the angle between two vectors:
      dot(a, b) / (norm(a) * norm(b))

    Args:
        vec_a: First embedding vector.
        vec_b: Second embedding vector.

    Returns:
        A float between -1 and 1, where 1 means identical direction.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)

    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
