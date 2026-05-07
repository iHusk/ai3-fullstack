"""One-time script to seed the enriched ChromaDB collection.

Handles the 5 req/min rate limit by sleeping between chunks.
Run after any concurrent experiments finish to avoid quota conflicts.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import anthropic
import chromadb
from pipeline.ingestion.chunker import chunk_document
from pipeline.embeddings.embed import embed_texts
from pipeline.ingestion.store import get_collection, CHROMA_PATH
from pipeline.retrieval.enriched import (
    ENRICHED_COLLECTION,
    N_QUESTIONS_PER_CHUNK,
    generate_questions_for_chunk,
)

# Rate limit: 5 req/min → 12s minimum gap. Use 13s to be safe.
SLEEP_BETWEEN_CHUNKS = 13

corpus = ROOT / "data" / "northbrook"
files = sorted(corpus.glob("*.md"))
print(f"Loading {len(files)} files from {corpus}")

chunks = []
for f in files:
    raw = chunk_document(f.read_text(encoding="utf-8"), source=f.name, doc_type="document")
    chunks.extend({"text": c.text, "metadata": c.metadata} for c in raw)

print(f"Loaded {len(chunks)} chunks total")
print(f"Seeding enriched collection (~{len(chunks) * SLEEP_BETWEEN_CHUNKS // 60} min at rate-limit pace)...")

# Rebuild collection from scratch
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
try:
    chroma_client.delete_collection(name=ENRICHED_COLLECTION)
    print("Deleted existing enriched collection.")
except ValueError:
    pass
collection = chroma_client.get_or_create_collection(
    name=ENRICHED_COLLECTION,
    metadata={"hnsw:space": "cosine"},
)

total_rows = 0
for idx, chunk in enumerate(chunks):
    chunk_text = chunk["text"]
    chunk_meta = chunk["metadata"]
    source = chunk_meta.get("source", "unknown")
    chunk_index = chunk_meta.get("chunk_index", idx)

    print(f"  Chunk {idx + 1}/{len(chunks)} ({source})...", end=" ", flush=True)

    questions = generate_questions_for_chunk(chunk_text)
    if not questions:
        print("no questions generated, skipping.")
        continue

    question_embeddings = embed_texts(questions)

    ids, documents, embeddings, metadatas = [], [], [], []
    for q_idx, (question, embedding) in enumerate(zip(questions, question_embeddings)):
        row_id = f"{source}_chunk{chunk_index}_q{q_idx}"
        ids.append(row_id)
        documents.append(chunk_text)
        embeddings.append(embedding)
        metadatas.append({**chunk_meta, "chunk_index": chunk_index, "source_question": question})

    collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    total_rows += len(ids)
    print(f"ok ({len(questions)} questions)")

    if idx < len(chunks) - 1:
        time.sleep(SLEEP_BETWEEN_CHUNKS)

print(f"\nDone. Stored {total_rows} rows ({len(chunks)} chunks x ~{N_QUESTIONS_PER_CHUNK} questions).")
