"""
rag.py -- Pipeline integration for Streamlit chat app.

INSTRUCTOR-MANAGED through Session 3.1. CODE FREEZE in effect after this version.
After Session 3.1, this file is yours to customize for Lab 2.
See the marked sections below for customization points.

This module wires the RAG pipeline into the Streamlit interface.
main.py imports: from app.rag import get_response, ChatResponse

Current version: Session 3.1 (safety-hardened)
    Changes from 2.1:
    - Added conversation history management (manage_history)
    - Added query rewriting for multi-turn retrieval (contextualize_query)
    - Added context assembly with document grouping (assemble_context)
    - Prompt now includes prior conversation for continuity
    - ChatResponse includes rewritten_query for transparency
    - 7 marked customization sections for Lab 2

    Session 3.1 changes:
    - Added input validation (defense layer 1)
    - Replaced manual system prompt with hardened prompt (defense layer 2)
    - Added output validation (defense layer 3)
    - Added span_id capture for Phoenix feedback annotations
    - ChatResponse includes span_id for feedback widget linking
"""

from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above app/)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


# ─── RETRIEVAL STRATEGY (Lab 2: HyDE + Voyage rerank-2) ───────
# HyDE generates a hypothetical answer first, then embeds THAT answer for
# search — closing the question/answer embedding gap. Then we rerank the
# top-N candidates with a Voyage cross-encoder for precision.
#
# Pattern: hyde_retrieve(top_k=20) → rerank(top_k=5)
# ──────────────────────────────────────────────────────────────
from pipeline.retrieval.hyde import hyde_retrieve as retrieve
from pipeline.retrieval.reranker import rerank

from pipeline.generation.generate import call_claude
from pipeline.context.assembler import contextualize_query, assemble_context
from pipeline.context.manager import manage_history
from pipeline.safety.guard import validate_input, build_hardened_prompt, validate_output
from opentelemetry import trace

from opentelemetry.trace import StatusCode

# Tracer for the RAG pipeline
_tracer = trace.get_tracer("rag-pipeline")

@dataclass
class ChatResponse:
    """Structured response from the RAG pipeline.

    Attributes:
        answer: The generated answer text from Claude.
        sources: Retrieved chunks used as context. Each dict contains
                 'text', 'metadata', and 'score' keys.
        rewritten_query: The query after contextualization. Shows how
                         the pipeline interpreted a follow-up question
                         for retrieval (may match original if standalone).
    """

    answer: str
    sources: list[dict] = field(default_factory=list)
    rewritten_query: str = ""
    span_id: str = ""



def get_response(question: str, messages: list[dict]) -> ChatResponse:
    """Get a grounded response from the RAG pipeline with safety guards.

    Pipeline steps:
      1. Capture span_id for Phoenix feedback annotations
      2. Validate input (defense layer 1)
      3. Manage history — trim conversation to fit context budget
      4. Contextualize — rewrite follow-ups into standalone queries
      5. Retrieve — find relevant chunks using the rewritten query
      6. Assemble — organize chunks into coherent reading order
      7. Build hardened prompt (defense layer 2)
      8. Generate — call Claude with the hardened prompt
      9. Validate output (defense layer 3)

      
      
    Args:
        question: The user's current question.
        messages: Conversation history (list of role/content dicts).

    Returns:
        A ChatResponse with the answer, supporting sources,
        the rewritten query used for retrieval, and span_id.
    """

    # Capture span for Phoenix feedback annotations
    # Create parent span for the entire pipeline
    with _tracer.start_as_current_span(
        "rag_pipeline",
        attributes={"input.value": question, "openinference.span.kind": "CHAIN"},
    ) as pipeline_span:
        ctx = pipeline_span.get_span_context()
        span_id = format(ctx.span_id, '016x') if ctx.span_id else ""

        # ... your existing pipeline code goes here, indented one more level ...
        # TIP: select all code below and press Tab to indent it



            
        # --- INPUT VALIDATION (defense layer 1) ---
        input_ok, input_reason = validate_input(question)
        if not input_ok:
            return ChatResponse(
                answer=input_reason,
                sources=[],
                rewritten_query="",
                span_id=span_id,
            )

        # ─── HISTORY MANAGEMENT (customization section 3 of 7) ────
        # Trim conversation history to fit within context budget.
        # Default: keep the last 10 messages (5 exchanges).
        #
        # Alternatives to explore:
        #   - Keep first + last messages (preserve opening context)
        #   - Summarize old messages instead of dropping them
        #   - Adjust max_messages based on message length
        # ──────────────────────────────────────────────────────────
        managed_history = manage_history(messages, max_messages=10)

        # ─── QUERY REWRITING (customization section 4 of 7) ──────
        # Rewrite follow-up questions so they stand alone for retrieval.
        # e.g., "How many days?" after discussing PTO becomes
        #        "How many PTO days does a Northbrook employee receive?"
        #
        # The rewriting prompt lives in pipeline/context/assembler.py.
        # Customize it there to change rewriting behavior.
        # ──────────────────────────────────────────────────────────
        rewritten = contextualize_query(managed_history, question)

        # ─── RETRIEVAL PARAMETERS (customization section 5 of 7) ─
        # HyDE+rerank pattern: over-fetch with bi-encoder recall, then
        # re-score with the cross-encoder for precision.
        #   TOP_K_RETRIEVE = 20  → broad candidate pool
        #   TOP_K_FINAL    = 5   → precision-ranked context for Claude
        # ──────────────────────────────────────────────────────────
        TOP_K_RETRIEVE = 20
        TOP_K_FINAL = 5

        with _tracer.start_as_current_span("retrieve_chunks") as ret_span:
            ret_span.set_attribute("openinference.span.kind", "RETRIEVER")
            ret_span.set_attribute("input.value", rewritten)
            candidates = retrieve(rewritten, top_k=TOP_K_RETRIEVE)
            ret_span.set_attribute("retrieve.top_k", TOP_K_RETRIEVE)
            ret_span.set_attribute("retrieve.n_results", len(candidates))
            if candidates:
                ret_span.set_attribute("retrieve.top_score", float(candidates[0].get("score", 0)))
            ret_span.set_status(StatusCode.OK)

        with _tracer.start_as_current_span("rerank_chunks") as rerank_span:
            rerank_span.set_attribute("openinference.span.kind", "RERANKER")
            rerank_span.set_attribute("input.value", rewritten)
            sources = rerank(rewritten, candidates, top_k=TOP_K_FINAL)
            rerank_span.set_attribute("rerank.top_k", TOP_K_FINAL)
            rerank_span.set_attribute("rerank.n_results", len(sources))
            if sources:
                rerank_span.set_attribute("rerank.sources",
                    ", ".join(s.get("metadata", {}).get("source", "") for s in sources))
                if "rerank_score" in sources[0]:
                    rerank_span.set_attribute("rerank.top_score", float(sources[0]["rerank_score"]))
            rerank_span.set_status(StatusCode.OK)

        if not sources:
            return ChatResponse(
                answer="I couldn't find relevant information in the Northbrook documents.",
                sources=[],
                rewritten_query=rewritten,
                span_id=span_id,
            )

        # ─── CONTEXT ASSEMBLY (customization section 6 of 7) ─────
        # Organize retrieved chunks into coherent reading order.
        # Groups by source document, sorts by chunk index, inserts
        # gap markers between non-consecutive chunks.
        #
        # The assembly logic lives in pipeline/context/assembler.py.
        # Customize it there to change grouping, ordering, or format.
        # ──────────────────────────────────────────────────────────
        assembled = assemble_context(sources)

        # --- SYSTEM PROMPT HARDENING (defense layer 2) ---
        # Build prompt sections: conversation history + assembled context + question
        sections = []
        recent = managed_history[-6:] if managed_history else []
        if recent:
            conversation_lines = []
            for msg in recent:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                conversation_lines.append(f"{role_label}: {msg['content']}")
            sections.append("## Conversation So Far\n" + "\n\n".join(conversation_lines))

        sections.append(assembled)  # Context goes into the hardened prompt

        full_context = "\n\n".join(sections)
        system_prompt = build_hardened_prompt(full_context)

        # The user message is just the current question (not the full context)
        user_message = question

        # ─── GENERATION SETTINGS (customization section 7 of 7) ──
        # Model, temperature, and token limits for Claude.
        # temperature=0.0 gives deterministic, grounded answers.
        #
        # Options to explore:
        #   - temperature=0.3 for slightly more varied responses
        #   - max_tokens=2048 for longer answers
        #   - model="claude-haiku-4-5" for faster/cheaper responses
        # ──────────────────────────────────────────────────────────
        with _tracer.start_as_current_span("generate_answer") as gen_span:
            gen_span.set_attribute("openinference.span.kind", "LLM")
            gen_span.set_attribute("input.value", user_message)
            answer = call_claude(user_message, system_prompt=system_prompt, temperature=0.0)
            gen_span.set_attribute("output.value", answer[:500])
            gen_span.set_status(StatusCode.OK)
        # --- OUTPUT VALIDATION (defense layer 3) ---
        source_names = [s.get("metadata", {}).get("source", "") for s in sources]
        output_ok, output_reason = validate_output(answer, source_names)
        if not output_ok:
            pipeline_span.set_attribute("output.value", output_reason)
            return ChatResponse(
                answer=output_reason,
                sources=sources,
                rewritten_query=rewritten,
                span_id=span_id,
            )
        pipeline_span.set_attribute("output.value", answer)
        return ChatResponse(answer=answer, sources=sources, rewritten_query=rewritten, span_id=span_id)
