"""
enriched.py -- Question Enrichment at Ingestion Time

At ingestion time, generate questions each chunk answers.
Embed EACH question as its own row in the vector store, with the
original chunk text as the 'documents' field.

This closes the embedding gap from the other direction: queries match
question embeddings directly (pure question-space), and we return the
chunk that the matched question points to.  While HyDE moves the
*query* into answer-space, enrichment moves the *documents* into
question-space at ingest time.  Both strategies address the same
fundamental problem -- questions and answers occupy different
neighborhoods in embedding space.

Session 1.1: We build these functions together in class.

Re-seeding the enriched collection (~3-5 min for the full corpus,
~$0.50 in API costs):

    python -c "
    from pipeline.ingestion.chunker import chunk_document
    from pipeline.retrieval.enriched import enrich_and_store
    from pathlib import Path
    import json

    chunks = []
    for f in sorted(Path('data').glob('*.txt')):
        chunks.extend(chunk_document(f.read_text(), source=f.stem, doc_type='document'))
    enrich_and_store(chunks)
    "
"""

from pathlib import Path

import anthropic
import chromadb

from pipeline.embeddings.embed import embed_texts
from pipeline.ingestion.store import get_collection, CHROMA_PATH


def _get_client():
    """Lazy Anthropic client — instantiated on first call, after env keys are set."""
    return anthropic.Anthropic()

ENRICHED_COLLECTION = "northbrook_enriched"

# -----------------------------------------------------------------------
# Lab 2 breadcrumb: Students can adjust this constant to generate more
# or fewer questions per chunk.  More questions = better recall but
# larger collection and higher seeding cost.
# -----------------------------------------------------------------------
N_QUESTIONS_PER_CHUNK = 3


def generate_questions_for_chunk(
    chunk_text: str, n_questions: int = N_QUESTIONS_PER_CHUNK
) -> list[str]:
    """Ask Claude what questions a chunk of text answers.

    Uses Claude to read a chunk and produce N natural-language questions
    that the chunk could answer.  These questions become the embeddings
    we store -- so retrieval matches question-to-question instead of
    question-to-answer.

    Args:
        chunk_text:   The raw text of a single chunk.
        n_questions:  How many questions to generate (default: 3).

    Returns:
        A list of question strings (may be shorter than *n_questions*
        if Claude returns fewer lines).
    """
    # ------------------------------------------------------------------
    # Lab 2 breadcrumb: The prompt below is a great customization point.
    # Students can tailor the question style (e.g., "ask questions a new
    # employee would ask" vs "ask questions a compliance auditor would
    # ask") to bias retrieval toward their target audience.
    # ------------------------------------------------------------------
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=256,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": (
                    f"What {n_questions} questions does this text passage "
                    f"answer? Return only the questions, one per line. "
                    f"No numbering.\n\n{chunk_text}"
                ),
            }
        ],
    )

    raw_text = message.content[0].text
    questions = [q.strip() for q in raw_text.split("\n") if q.strip()]
    return questions


def enrich_and_store(
    chunks: list[dict],
    collection_name: str = ENRICHED_COLLECTION,
) -> None:
    """Generate questions for each chunk and store them in a dedicated collection.

    For every chunk we:
      1. Generate N questions via Claude.
      2. Embed all N questions in a single batch (Voyage AI).
      3. Store one row per question in ChromaDB, with the *original
         chunk text* as the document field.

    This means retrieval queries match against question embeddings
    (question-space) and return the chunk the question points to.

    The function is **idempotent** -- it deletes the existing collection
    before writing so students can safely re-run without duplicates.

    Note: Seeding takes ~3-5 minutes for the full Northbrook corpus and
    costs approximately $0.50 in API calls (Claude + Voyage AI).

    Args:
        chunks:           List of chunk dicts, each with at minimum
                          ``text`` and ``metadata`` keys.  ``metadata``
                          must include ``source`` and ``chunk_index``.
        collection_name:  Name of the ChromaDB collection to write to.
    """
    # Idempotent: wipe and recreate so re-runs are safe
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        chroma_client.delete_collection(name=collection_name)
    except ValueError:
        pass  # Collection doesn't exist yet -- that's fine
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    total_rows = 0

    for idx, chunk in enumerate(chunks):
        chunk_text = chunk["text"]
        chunk_meta = chunk["metadata"]
        source = chunk_meta.get("source", "unknown")
        chunk_index = chunk_meta.get("chunk_index", idx)

        print(f"Chunk {idx + 1}/{len(chunks)}...")

        # Step 1: Generate questions for this chunk
        questions = generate_questions_for_chunk(chunk_text)
        if not questions:
            continue

        # Step 2: Embed all questions in one batch
        question_embeddings = embed_texts(questions)

        # Step 3: Store one row per question
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for q_idx, (question, embedding) in enumerate(
            zip(questions, question_embeddings)
        ):
            row_id = f"{source}_chunk{chunk_index}_q{q_idx}"
            ids.append(row_id)
            documents.append(chunk_text)  # Return original chunk on retrieval
            embeddings.append(embedding)
            metadatas.append(
                {
                    **chunk_meta,
                    "chunk_index": chunk_index,
                    "source_question": question,
                }
            )

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        total_rows += len(ids)

    n_questions = N_QUESTIONS_PER_CHUNK
    print(
        f"\nStored {len(chunks)} chunks x {n_questions} questions "
        f"= {total_rows} rows"
    )


def enriched_retrieve(
    question: str,
    top_k: int = 5,
    collection_name: str = ENRICHED_COLLECTION,
) -> list[dict]:
    """Retrieve chunks by matching against stored question embeddings.

    Embeds the user's question, then searches the enriched collection
    where every row is a *generated question* pointing back to its
    source chunk.  Because we store N questions per chunk, we over-fetch
    and then deduplicate so the caller gets ``top_k`` unique chunks.

    Args:
        question:         The user's question.
        top_k:            Number of unique chunks to return (default: 5).
        collection_name:  Name of the enriched ChromaDB collection.

    Returns:
        A list of dicts (length <= top_k), each containing:
            - text:              The original chunk content.
            - metadata:          The chunk's stored metadata.
            - score:             Cosine similarity (1 - distance).
            - matched_question:  The generated question that matched.

    Raises:
        RuntimeError: If the collection is empty (enrichment has not
                      been run yet).
    """
    collection = get_collection(collection_name)

    # Guard: fail fast if the collection hasn't been seeded yet
    if collection.count() == 0:
        raise RuntimeError(
            f"Collection '{collection_name}' is empty. "
            "Run enrich_and_store() first to populate it. "
            "See the docstring for usage."
        )

    question_embedding = embed_texts([question])[0]

    # Over-fetch: each chunk has N_QUESTIONS_PER_CHUNK rows, so we need
    # to pull extra to guarantee top_k unique chunks after dedup.
    n_fetch = top_k * N_QUESTIONS_PER_CHUNK

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=n_fetch,
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # Deduplicate: keep the highest-scoring hit per chunk_index
    best_per_chunk: dict[int, dict] = {}

    for doc, meta, dist in zip(documents, metadatas, distances):
        score = 1 - dist
        chunk_idx = meta.get("chunk_index", -1)

        if chunk_idx not in best_per_chunk or score > best_per_chunk[chunk_idx]["score"]:
            best_per_chunk[chunk_idx] = {
                "text": doc,
                "metadata": meta,
                "score": score,
                "matched_question": meta.get("source_question", ""),
            }

    # Sort by score descending and return top_k unique chunks
    sources = sorted(best_per_chunk.values(), key=lambda s: s["score"], reverse=True)

    return sources[:top_k]
